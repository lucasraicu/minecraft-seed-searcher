"""Deterministic scale validation for automation streaming retention, restart idempotence, and >16MiB paged manifests."""
import hashlib
import resource
import time
from pathlib import Path


from seed_search.catalog.harvest import AutomationLedger, HarvestQueue, _validate_rank
from seed_search.catalog.models import (
    empty_observation_v2,
    identity,
    validate_identity,
    world_id,
)
from seed_search.catalog.registry import canonical_json, digest
from seed_search.catalog.store import AutomationStore


class OfflineLedgerOracle:
    """Keep all per-world best ranks, then full-sort; never stream-evict."""
    def __init__(self, objectives):
        self.objectives=objectives;self.receipts={};self.offers={}

    def offer(self,receipt,offers):
        self.receipts[receipt['world_id']]=receipt
        for row in offers:
            key=(row['objective_id'],receipt['world_id'])
            if key not in self.offers or row['rank']<self.offers[key]['rank']:
                self.offers[key]=dict(row,world_id=receipt['world_id'])

    def population(self):return len(self.receipts)

    def members(self,objective_id=None):
        result=[]
        for objective,capacity in sorted(self.objectives.items()):
            if objective_id is not None and objective!=objective_id:continue
            rows=[r for (oid,_),r in self.offers.items() if oid==objective]
            result.extend(sorted(rows,key=lambda r:(r['rank'],r['world_id']))[:capacity])
        return result

    def retained_worlds(self):return sorted({r['world_id'] for r in self.members()})


def _make_obs(seed: str) -> dict:
    return empty_observation_v2(
        identity(seed, model_id="MC_26_50", native_sha256="a" * 64, source_sha256="b" * 64)
    )


def test_500_world_streaming_retention_and_restart_idempotence(tmp_path: Path):
    """500 distinct valid worlds with deterministic ties/reoffers match offline oracle exactly."""
    t0 = time.perf_counter()
    objectives = {"obj_alpha": 10, "obj_beta": 15, "obj_gamma": 5}
    oracle = OfflineLedgerOracle(objectives)

    with HarvestQueue(tmp_path) as queue:
        store = AutomationStore(tmp_path)
        ledger = AutomationLedger(queue, policy_revision="c" * 64, objectives=objectives)

        receipts = []

        # 1. Stream 500 distinct valid empty_observation_v2 worlds
        for i in range(500):
            obs = _make_obs(str(i))
            wid = world_id(obs["identity"])
            oid = digest(obs)
            artifact = store.stage(obs, [])
            receipt = dict(
                world_id=wid,
                identity=obs["identity"],
                observation_id=oid,
                artifact=artifact,
                evaluations=[],
                replay={"resumable": False},
            )
            receipts.append(receipt)

            # Generate deterministic multi-objective offers with numeric ties
            offers = []
            if i % 2 == 0:
                offers.append(dict(
                    objective_id="obj_alpha",
                    rank=[i % 20],  # Numeric ties across worlds (e.g. 0, 20, 40 -> rank [0])
                    member=dict(world_id=wid, source_observation_id=oid),
                ))
            if i % 3 != 0:
                offers.append(dict(
                    objective_id="obj_beta",
                    rank=[(500 - i) % 30],  # Numeric ties across worlds
                    member=dict(world_id=wid, source_observation_id=oid),
                ))
            if i % 5 == 0:
                offers.append(dict(
                    objective_id="obj_gamma",
                    rank=[i // 50],  # Numeric ties in bins of 50
                    member=dict(world_id=wid, source_observation_id=oid),
                ))

            ledger.offer(receipt, offers)
            oracle.offer(receipt, offers)

        # 2. Deterministic reoffers: idempotent, rank upgrades, and non-winning downgrades
        reoffer_count = 0
        for i in range(0, 500, 10):
            reoffer_count += 1
            receipt = receipts[i]
            wid = receipt["world_id"]
            oid = receipt["observation_id"]

            if i % 30 == 0:
                # Rank improvement to beat earlier winners
                reoffers = [dict(
                    objective_id="obj_alpha",
                    rank=[-1],
                    member=dict(world_id=wid, source_observation_id=oid),
                )]
            elif i % 30 == 10:
                # Idempotent reoffer with same rank
                reoffers = [dict(
                    objective_id="obj_beta",
                    rank=[(500 - i) % 30],
                    member=dict(world_id=wid, source_observation_id=oid),
                )]
            else:
                # Worse rank: ignored if currently winning on same observation
                reoffers = [dict(
                    objective_id="obj_alpha",
                    rank=[9999],
                    member=dict(world_id=wid, source_observation_id=oid),
                )]

            ledger.offer(receipt, reoffers)
            oracle.offer(receipt, reoffers)

        t_stream = time.perf_counter()

        # 3. Assert exact equality with offline oracle
        assert ledger.population() == 500
        assert oracle.population() == 500
        assert ledger.population() == oracle.population()

        retained = ledger.retained_worlds()
        oracle_retained = oracle.retained_worlds()
        assert retained == oracle_retained
        assert len(retained) > 0
        assert len(retained) <= sum(objectives.values())

        members = ledger.members()
        oracle_members = oracle.members()
        assert members == oracle_members

        for obj_id in objectives:
            obj_members = ledger.members(obj_id)
            oracle_obj_members = oracle.members(obj_id)
            assert obj_members == oracle_obj_members
            assert len(obj_members) == objectives[obj_id]
            # Verify internal monotonic rank ordering
            ranks = [m["rank"] for m in obj_members]
            assert ranks == sorted(ranks, key=lambda r: _validate_rank(r))

        # Every retained world must bind a real receipt
        for wid in retained:
            rec = ledger.receipt(wid)
            assert rec is not None
            assert rec["world_id"] == wid
            assert world_id(rec["identity"]) == wid

        # Dry-run cleanup candidate count matches exact unreferenced population
        cleanup_report = store.cleanup(ledger, mode="dry_run")
        assert len(cleanup_report["candidates"]) == 500 - len(retained)

        # 4. Restart idempotence: reconstruct ledger from disk
        t_restart_start = time.perf_counter()
        reopened = AutomationLedger(queue, policy_revision="c" * 64, objectives=objectives)
        assert reopened.population() == 500
        assert reopened.generation() == ledger.generation()
        assert reopened.retained_worlds() == retained
        assert reopened.members() == members
        for obj_id in objectives:
            assert reopened.members(obj_id) == ledger.members(obj_id)

        # 5. Publication and snapshot verification
        sid = store.publish(reopened)
        assert isinstance(sid, str) and len(sid) == 64
        # Re-publish is strictly idempotent
        assert store.publish(reopened) == sid

        snapshot = store.snapshot(sid)
        assert snapshot["generation"] == reopened.generation()
        assert snapshot["population_worlds"] == 500
        assert [w["world_id"] for w in snapshot["worlds"]] == retained
        assert snapshot["memberships"] == members

        # Iter_worlds streams all retained bundles without reloading
        streamed_bundles = list(store.iter_worlds(sid))
        assert len(streamed_bundles) == len(retained)
        for b in streamed_bundles:
            assert b["revision"] == "catalog-world-bundle-v2"
            bwid = world_id(b["observation"]["identity"])
            assert bwid in retained
            assert store.world(sid, bwid) == b

        t_end = time.perf_counter()

        disk_bytes = sum(p.stat().st_size for p in tmp_path.rglob("*") if p.is_file())
        rss_bytes = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if __import__("sys").platform=="darwin" else 1024)

        print(
            f"\n[SCALE TEST 1: 500-World Streaming Retention & Restart Idempotence]\n"
            f"  Worlds offered: 500 (distinct valid empty_observation_v2)\n"
            f"  Reoffers evaluated: {reoffer_count}\n"
            f"  Streaming offer duration: {t_stream - t0:.3f}s\n"
            f"  Restart + publish duration: {t_end - t_restart_start:.3f}s\n"
            f"  Total test duration: {t_end - t0:.3f}s (suite limit < 120s)\n"
            f"  Population: {ledger.population()}\n"
            f"  Retained winning worlds: {len(retained)}\n"
            f"  Winning memberships: {len(members)}\n"
            f"  Published Snapshot ID: {sid}\n"
            f"  Disk usage: {disk_bytes / (1024 * 1024):.2f} MiB (limit <= 500 MiB)\n"
            f"  Peak RSS: {rss_bytes / (1024 * 1024):.2f} MiB (limit <= 2048 MiB)"
        )


def test_large_logical_manifest_paging_roundtrip(tmp_path: Path):
    """Separate valid >16MiB logical manifest roundtrips real _write_manifest/_resolve_manifest using DEFAULT production page limits."""
    t0 = time.perf_counter()
    store = AutomationStore(tmp_path)

    # Verify DEFAULT production page limits remain untouched
    assert store._PAGE_THRESHOLD_BYTES == 8 * 1024 * 1024
    assert store._PAGE_ITEM_LIMIT == 2048
    assert store._PAGE_BYTE_LIMIT == 4 * 1024 * 1024
    assert store._INDEX_PAGE_LIMIT == 1024

    n_slots = 20000  # <= 105644 declared capacity
    base_ident = identity("0", model_id="MC_26_50", native_sha256="a" * 64, source_sha256="b" * 64)
    validate_identity(base_ident)

    worlds = []
    memberships = []

    for i in range(n_slots):
        ident = dict(base_ident, seed=str(i))
        wid = world_id(ident)
        obs_id = hashlib.sha256(f"scale_obs_{i}".encode("ascii")).hexdigest()
        art_sha = hashlib.sha256(f"scale_art_{i}".encode("ascii")).hexdigest()
        art = dict(
            sha256=art_sha,
            relative_key=f"{art_sha[:2]}/{art_sha}.json.gz",
            byte_length=128,
            uncompressed_length=256,
            codec="gzip",
        )
        worlds.append(dict(
            world_id=wid,
            identity=ident,
            observation_id=obs_id,
            artifact=art,
        ))
        memberships.append(dict(
            objective_id="scale_top",
            world_id=wid,
            rank=[i],
            member=dict(
                world_id=wid,
                source_observation_id=obs_id,
            ),
        ))

    manifest = dict(
        revision="catalog-snapshot-v2",
        policy_revision="c" * 64,
        generation=1,
        population_worlds=n_slots,
        worlds=worlds,
        memberships=memberships,
    )

    t_gen = time.perf_counter()
    raw_manifest = canonical_json(manifest)
    logical_bytes = len(raw_manifest)
    logical_sha = digest(manifest)

    # Manifest must be strictly > 16 MiB
    assert logical_bytes > 16 * 1024 * 1024, f"Expected >16MiB logical manifest, got {logical_bytes} bytes"
    assert len(worlds) <= 105644
    assert len(memberships) <= 105644

    # Execute physical manifest paging using default limits
    t_write_start = time.perf_counter()
    index_artifact = store._write_manifest(manifest)
    t_write_end = time.perf_counter()

    index_payload = store.artifacts.get_json(index_artifact)
    assert index_payload["revision"] == "catalog-snapshot-index-v2"
    assert index_payload["policy_revision"] == manifest["policy_revision"]
    assert index_payload["generation"] == manifest["generation"]
    assert index_payload["population_worlds"] == manifest["population_worlds"]

    pages = index_payload["pages"]
    assert len(pages) > 1, f"Expected pagecount > 1, got {len(pages)}"

    world_pages = [p for p in pages if p["kind"] == "worlds"]
    member_pages = [p for p in pages if p["kind"] == "memberships"]
    assert len(world_pages) > 1
    assert len(member_pages) > 1

    # Verify each physical page obeys production constraints
    for ref in pages:
        assert set(ref.keys()) == {"kind", "count", "artifact"}
        assert 1 <= ref["count"] <= store._PAGE_ITEM_LIMIT
        assert ref["artifact"]["uncompressed_length"] <= store._PAGE_BYTE_LIMIT
        assert ref["artifact"]["byte_length"] <= ref["artifact"]["uncompressed_length"]

        page_file = store.objects_dir / ref["artifact"]["relative_key"]
        assert page_file.is_file()
        assert page_file.stat().st_size <= store._PAGE_BYTE_LIMIT

        page_data = store.artifacts.get_json(ref["artifact"])
        assert page_data["revision"] == "catalog-snapshot-page-v2"
        assert page_data["kind"] == ref["kind"]
        assert page_data["count"] == ref["count"] == len(page_data["items"])
        assert len(canonical_json(page_data)) <= store._PAGE_BYTE_LIMIT

    # Resolve manifest through CAS pages
    t_resolve_start = time.perf_counter()
    resolved_manifest = AutomationStore(tmp_path)._resolve_manifest(index_artifact)
    t_resolve_end = time.perf_counter()

    # Exact parity and logical digest preservation
    resolved_sha = digest(resolved_manifest)
    assert resolved_sha == logical_sha
    assert canonical_json(resolved_manifest) == raw_manifest
    assert resolved_manifest == manifest

    t_end = time.perf_counter()
    disk_bytes = sum(p.stat().st_size for p in tmp_path.rglob("*") if p.is_file())
    rss_bytes = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if __import__("sys").platform=="darwin" else 1024)

    print(
        f"\n[SCALE TEST 2: >16MiB Logical Manifest CAS Paging Roundtrip]\n"
        f"  Total slots (worlds/members): {n_slots} (declared cap <= 105644)\n"
        f"  Generation duration: {t_gen - t0:.3f}s\n"
        f"  Logical uncompressed size: {logical_bytes / (1024 * 1024):.2f} MiB ({logical_bytes} bytes > 16 MiB)\n"
        f"  Logical SHA256: {logical_sha}\n"
        f"  _write_manifest duration: {t_write_end - t_write_start:.3f}s\n"
        f"  Physical pages generated: {len(pages)} (pagecount > 1, cap <= 1024)\n"
        f"    - World pages: {len(world_pages)} (items <= 2048, page uncompressed <= 4 MiB)\n"
        f"    - Membership pages: {len(member_pages)} (items <= 2048, page uncompressed <= 4 MiB)\n"
        f"  _resolve_manifest duration: {t_resolve_end - t_resolve_start:.3f}s\n"
        f"  Total test duration: {t_end - t0:.3f}s (suite limit < 120s)\n"
        f"  CAS disk bytes: {disk_bytes / (1024 * 1024):.2f} MiB (limit <= 500 MiB)\n"
        f"  Peak RSS: {rss_bytes / (1024 * 1024):.2f} MiB (limit <= 2048 MiB)\n"
        f"  Candid operational limits: Verified DEFAULT production page limits (_PAGE_THRESHOLD_BYTES=8MiB, _PAGE_BYTE_LIMIT=4MiB, _PAGE_ITEM_LIMIT=2048, _INDEX_PAGE_LIMIT=1024)"
    )
