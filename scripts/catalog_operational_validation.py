#!/usr/bin/env python3
"""Operational validation harness for larger-scale segmented catalog operation.

Generates validated synthetic worlds with 243 layouts per world (81 anchors x 3 borders),
publishes them in bounded atomic batches, and validates Cold/Warm query parity against an
independent streaming exhaustive oracle with bounded memory.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import random
import resource
import statistics
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from seed_search.catalog import codec
from seed_search.catalog.evaluation import heldout_cases
from seed_search.catalog.geometry import bounds_for
from seed_search.catalog.ingestion import atomic_json
from seed_search.catalog import models
from seed_search.catalog.query import _rank
from seed_search.catalog.registry import (
    BIOMES,
    ENVELOPE,
    FEATURE_IDS,
    POLICY,
    REGISTRY,
    REGISTRY_REVISION,
    SIDES,
    STRUCTURES,
    digest,
)
from seed_search.catalog.request import validate_request
from seed_search.catalog.segments import SegmentedCatalog
from seed_search.catalog.service import CatalogService
from seed_search.catalog.summaries import summarize
from seed_search.seeds import parse_seed

SYNTHETIC_MODEL_ID = "synthetic-operational-v1"
SYNTHETIC_NATIVE_SHA = "a" * 64
SYNTHETIC_SOURCE_SHA = "b" * 64
SYNTHETIC_NOTE = (
    "Explicitly fabricated synthetic operational validation data; "
    "not natural diversity, player-demand evidence, or real Minecraft generation."
)


def get_current_rss_bytes() -> int:
    """Return process peak RSS in bytes."""
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform != "darwin":
        rss *= 1024
    return int(rss)


def tree_bytes(root: Path) -> int:
    """Compute total storage in bytes of an un-symlinked tree."""
    if not root.exists():
        return 0
    total = 0
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"Symlink rejected in catalog tree: {path}")
        try:
            if path.is_file():
                total += path.stat().st_size
        except FileNotFoundError:
            pass
    return total


def check_limits(
    start_time: float,
    seconds_budget: int,
    max_rss_bytes: int,
    max_bytes: int,
    output_path: Path,
) -> None:
    """Enforce runtime, RSS, and storage caps before operations."""
    elapsed = time.monotonic() - start_time
    if elapsed > seconds_budget:
        raise TimeoutError(
            f"Wall-clock allowance exceeded: {elapsed:.2f}s > {seconds_budget}s"
        )
    current_rss = get_current_rss_bytes()
    if current_rss > max_rss_bytes:
        raise MemoryError(
            f"Process peak RSS exceeded cap: {current_rss} > {max_rss_bytes} bytes"
        )
    current_disk = tree_bytes(output_path)
    if current_disk > max_bytes:
        raise OSError(
            f"Output storage exceeded cap: {current_disk} > {max_bytes} bytes"
        )


def make_fixture(seed: int | str, template: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a strictly validated synthetic observation with 243-layout coverage.

    Replaces engine identity with fixed synthetic operational identity. Never retains
    real engine identities with fake seeds. Covers all 14 structures and 9 biome families.
    """
    seed_val = parse_seed(seed)
    seed_str = str(seed_val)
    seed_u64 = seed_val & ((1 << 64) - 1)

    ident = models.identity(
        seed_str,
        model_id=SYNTHETIC_MODEL_ID,
        native_sha256=SYNTHETIC_NATIVE_SHA,
        source_sha256=SYNTHETIC_SOURCE_SHA,
        world_settings_id="default",
    )

    if template is None:
        obs = models.empty_observation(ident)

        # 1. Structure inventories (14 structures)
        for f in STRUCTURES:
            fid = f["id"]
            slot = f["slot"]
            rng = random.Random(f"synthetic-operational:{seed_str}:{slot}")
            pts: set[tuple[int, int]] = set()

            # Deterministic base anchors for village/trial chamber so representative queries find matches
            if slot == 0:  # structure.village
                vx = ((seed_val * 31 + 17) % 15 - 7) * 32
                vz = ((seed_val * 47 + 23) % 15 - 7) * 32
                pts.add((vx, vz))
                pts.add((vx + 256, vz + 128))
            elif slot == 1:  # structure.trial_chamber
                pts.add(((seed_val * 19) % 31 * 64 - 960, (seed_val * 29) % 31 * 64 - 960))
            elif slot == 4:  # structure.mansion
                pts.add(((seed_val * 13) % 41 * 64 - 1280, (seed_val * 23) % 41 * 64 - 1280))

            num_pts = 6 + (abs(seed_val) + slot) % 8
            while len(pts) < num_pts:
                pts.add((rng.randint(-3000, 3000), rng.randint(-3000, 3000)))

            obs["structures"][fid] = [list(p) for p in sorted(pts)]
            obs["coverage"][fid] = {
                "status": "complete",
                "bounds": list(ENVELOPE),
                "method_id": "predictor_viable_starts_v1",
            }

        # 2. Complete 25,600-point biome lattice at y=63, stride=64
        obs["biome_names"] = {str(b["slot"]): b["canonical_members"][0] for b in BIOMES}
        biomes = []
        for x in range(-5120, 5120, 64):
            for z in range(-5120, 5120, 64):
                bid = ((x // 64 + 80) // 16 + (z // 64 + 80) // 16 + seed_u64) % 9
                biomes.append([x, 63, z, bid])
        obs["biomes"] = biomes

        for b in BIOMES:
            obs["coverage"][b["id"]] = {
                "status": "complete",
                "bounds": list(ENVELOPE),
                "method_id": "predictor_world_lattice_y63_stride64_v1",
            }

        return models.validate_observation(obs)

    # Transform from provided diverse template observation
    obs = copy.deepcopy(template)
    obs["identity"] = ident

    # Deterministically transform structure points (flip, rotate, translate) without cloned coordinates
    rot = seed_u64 % 4
    flip = ((seed_u64 // 4) % 2) == 1
    dx = (((seed_val * 37 + 13) % 41) - 20) * 64
    dz = (((seed_val * 53 + 17) % 41) - 20) * 64

    new_structures = {}
    for f in STRUCTURES:
        fid = f["id"]
        raw_pts = obs.get("structures", {}).get(fid, [])
        transformed: set[tuple[int, int]] = set()
        for p in raw_pts:
            x, z = int(p[0]), int(p[1])
            if rot == 1:
                x, z = -z, x
            elif rot == 2:
                x, z = -x, -z
            elif rot == 3:
                x, z = z, -x
            if flip:
                x = -x
            nx, nz = x + dx, z + dz
            if -5120 <= nx < 5120 and -5120 <= nz < 5120:
                transformed.add((nx, nz))
            elif -5120 <= x < 5120 and -5120 <= z < 5120:
                transformed.add((x, z))
        new_structures[fid] = [list(p) for p in sorted(transformed)]
        obs["coverage"][fid] = {
            "status": "complete",
            "bounds": list(ENVELOPE),
            "method_id": "predictor_viable_starts_v1",
        }
    obs["structures"] = new_structures

    # Keep biome lattice point coverage/IDs valid; never translate lattice outside bounds
    if len(obs.get("biomes", [])) != 25600:
        biomes = []
        for x in range(-5120, 5120, 64):
            for z in range(-5120, 5120, 64):
                bid = ((x // 64 + 80) // 16 + (z // 64 + 80) // 16 + seed_u64) % 9
                biomes.append([x, 63, z, bid])
        obs["biomes"] = biomes
        obs["biome_names"] = {str(b["slot"]): b["canonical_members"][0] for b in BIOMES}
    else:
        valid_bids = [
            int(k)
            for k, name in obs.get("biome_names", {}).items()
            if not name.startswith("unknown")
        ]
        if valid_bids:
            shift = seed_u64 % len(valid_bids)
            mapping = {
                valid_bids[i]: valid_bids[(i + shift) % len(valid_bids)]
                for i in range(len(valid_bids))
            }
            for pt in obs["biomes"]:
                pt[3] = mapping.get(pt[3], pt[3])

    for b in BIOMES:
        obs["coverage"][b["id"]] = {
            "status": "complete",
            "bounds": list(ENVELOPE),
            "method_id": "predictor_world_lattice_y63_stride64_v1",
        }

    obs["bounds"] = list(ENVELOPE)
    return models.validate_observation(obs)


def streaming_exhaustive_oracle(
    store: SegmentedCatalog,
    snapshot_id: str,
    request: dict[str, Any],
    limit: int = 50,
) -> tuple[list[dict[str, Any]], int]:
    """Streaming exhaustive oracle evaluating all leaf segments with no request filter.

    Decodes segments one leaf at a time, computes per-world best layouts via query._rank(..., keep_keys=True),
    deduplicates globally by min_sort_key across leaf boundaries, and keeps zero full decoded
    corpora in memory.
    """
    req = validate_request(request, snapshot_id=snapshot_id)
    best_by_world: dict[str, dict[str, Any]] = {}
    layouts_seen = 0

    # Stream over all leaf segments without passing request (no index filtering)
    for segment in store.iter_segments(snapshot_id):
        rows = segment["layouts"]
        layouts_seen += len(rows)
        ranked = _rank(rows, req, limit=len(rows), validate_records=False, keep_keys=True)
        for cand in ranked:
            wid = cand["world_id"]
            if wid not in best_by_world or cand["_sort_key"] < best_by_world[wid]["_sort_key"]:
                best_by_world[wid] = cand

    globally_sorted = sorted(best_by_world.values(), key=lambda c: c["_sort_key"])
    top_k = globally_sorted[:limit]

    clean_results = []
    for r in top_k:
        entry = dict(r)
        entry.pop("_sort_key", None)
        clean_results.append(entry)

    return clean_results, layouts_seen


def build_representative_queries(snapshot_id: str, header: dict[str, Any]) -> list[dict[str, Any]]:
    """Build 18 queries: 3 borders x 2 anchor modes x 3 condition types (broad, selective, mixed)."""
    base_template = heldout_cases()["cases"][0]["template"]
    query_types = [
        ("broad", []),
        (
            "selective",
            [
                {
                    "rule": "required",
                    "kind": "structure_count",
                    "feature": "structure.village",
                    "at_least": 1,
                    "scope": {"kind": "near_base", "radius": 512},
                },
                {
                    "rule": "required",
                    "kind": "biome_witness",
                    "any_of": ["biome.cherry_grove"],
                    "scope": {"kind": "near_base", "radius": 512},
                },
            ],
        ),
        (
            "mixed",
            [
                {
                    "rule": "required",
                    "kind": "structure_count",
                    "feature": "structure.village",
                    "at_least": 1,
                    "scope": {"kind": "near_base", "radius": 1024},
                },
                {
                    "rule": "preferred",
                    "kind": "biome_witness",
                    "any_of": ["biome.cherry_grove"],
                    "importance": 5,
                    "scope": {"kind": "near_base", "radius": 512},
                },
                {
                    "rule": "preferred",
                    "kind": "structure_count",
                    "feature": "structure.mansion",
                    "at_least": 1,
                    "importance": 3,
                    "scope": {"kind": "inside_border"},
                },
            ],
        ),
    ]

    queries = []
    for side in SIDES:
        for mode in ("origin", "recommended"):
            for q_type, rows in query_types:
                req = copy.deepcopy(base_template)
                req["catalog_snapshot_id"] = snapshot_id
                req["game_build_id"] = header["game_build_id"]
                req["world_settings_id"] = header["world_settings_id"]
                req["border_side"] = side
                req["anchor_mode"] = mode
                req["rows"] = rows
                validated = validate_request(
                    req,
                    snapshot_id=snapshot_id,
                    game_build_id=header["game_build_id"],
                    world_settings_id=header["world_settings_id"],
                )
                queries.append(
                    {
                        "query_type": q_type,
                        "border_side": side,
                        "anchor_mode": mode,
                        "request": validated,
                    }
                )
    return queries


def run(
    output: Path | str,
    worlds: int = 10,
    batch_size: int = 5,
    source_root: Path | str | None = None,
    source_snapshot: str | None = None,
    seconds: int = 300,
    max_bytes: int = 4 * 1024 * 1024 * 1024,
    max_rss_bytes: int = 4 * 1024 * 1024 * 1024,
) -> dict[str, Any]:
    """Execute operational catalog validation harness with strict parameter caps."""
    # 1. Parameter validation
    if type(worlds) is not int or not 1 <= worlds <= 2000:
        raise ValueError("worlds must be an integer between 1 and 2000")
    if type(batch_size) is not int or not 1 <= batch_size <= 10:
        raise ValueError("batch_size must be an integer between 1 and 10")
    if type(seconds) is not int or not 1 <= seconds <= 3600:
        raise ValueError("seconds must be an integer between 1 and 3600")
    if type(max_bytes) is not int or max_bytes <= 0 or max_bytes > 4 * 1024 * 1024 * 1024:
        raise ValueError("max_bytes must be an integer between 1 and 4GiB (4294967296 bytes)")
    if type(max_rss_bytes) is not int or max_rss_bytes <= 0 or max_rss_bytes > 4 * 1024 * 1024 * 1024:
        raise ValueError("max_rss_bytes must be an integer between 1 and 4GiB (4294967296 bytes)")

    out_path = Path(output).resolve()
    if out_path.exists():
        raise FileExistsError(f"Output directory {out_path} already exists; new owned root required")
    out_path.mkdir(parents=True, exist_ok=False)

    src_path: Path | None = None
    if source_root is not None or source_snapshot is not None:
        if source_root is None or source_snapshot is None:
            raise ValueError("source_root and source_snapshot must both be provided when using source templates")
        src_path = Path(source_root).resolve()
        if not src_path.is_dir():
            raise ValueError(f"source_root {src_path} is not an existing directory")
        if out_path == src_path or out_path in src_path.parents or src_path in out_path.parents:
            raise ValueError("source_root and output directory cannot be identical or nested")
        if (
            not isinstance(source_snapshot, str)
            or len(source_snapshot) != 64
            or any(c not in "0123456789abcdef" for c in source_snapshot)
        ):
            raise ValueError("source_snapshot must be a 64-character hex string")

    start_time = time.monotonic()
    catalog_dir = out_path / "catalog"
    parent: str | None = None

    # Load source identities lazily if source provided
    source_idents = []
    if src_path is not None and source_snapshot is not None:
        with SegmentedCatalog(src_path) as src_store:
            source_idents = src_store.identities(source_snapshot)
            if not source_idents:
                raise ValueError(f"No world identities found in source snapshot {source_snapshot}")

    # 2. Publication in bounded batches
    with SegmentedCatalog(catalog_dir, leaf_entries=256, fanout=128) as store:
        for batch_start in range(0, worlds, batch_size):
            check_limits(start_time, seconds, max_rss_bytes, max_bytes, out_path)
            batch_end = min(batch_start + batch_size, worlds)
            batch_obs = []
            batch_summaries = []

            for idx in range(batch_start, batch_end):
                template = None
                if src_path is not None and source_snapshot is not None:
                    src_ident = source_idents[idx % len(source_idents)]
                    with SegmentedCatalog(src_path) as src_store:
                        template = src_store.observation(source_snapshot, models.world_id(src_ident))

                obs = make_fixture(idx, template=template)
                summaries = summarize(obs)
                batch_obs.append(obs)
                batch_summaries.extend(summaries)

            parent = store.publish(batch_obs, batch_summaries, parent=parent)
            progress = {
                "stage": "publishing",
                "completed_batches": (batch_end + batch_size - 1) // batch_size,
                "completed_worlds": batch_end,
                "completed_layouts": batch_end * 243,
                "current_snapshot_id": parent,
                "source_fixture_identity": dict(
                    edition="bedrock",
                    game_build_id=f"research:{SYNTHETIC_MODEL_ID}",
                    world_settings_id="default",
                    model_id=SYNTHETIC_MODEL_ID,
                    native_sha256=SYNTHETIC_NATIVE_SHA,
                    source_sha256=SYNTHETIC_SOURCE_SHA,
                    registry_revision=REGISTRY_REVISION,
                ),
                "completed_queries": 0,
                "measurements": [],
                "wall_seconds": time.monotonic() - start_time,
            }
            atomic_json(out_path / "progress.json", progress)

        audit = store.audit(parent)
        info = store.info(parent)

    publish_seconds = time.monotonic() - start_time

    # 3. Exercise persistent closed/reopened catalog
    service = CatalogService(catalog_dir, query_seconds=float(seconds))
    queries = build_representative_queries(parent, info["header"])
    measurements = []
    queries_start = time.monotonic()

    with SegmentedCatalog(catalog_dir) as oracle_store:
        for q in queries:
            check_limits(start_time, seconds, max_rss_bytes, max_bytes, out_path)

            # Cold execution (un-cached)
            cold_before = time.monotonic()
            cold_result = service.query(dict(request=q["request"], page_size=50))
            cold_seconds = time.monotonic() - cold_before

            # Warm execution (cached)
            warm_before = time.monotonic()
            warm_result = service.query(dict(request=q["request"], page_size=50))
            warm_seconds = time.monotonic() - warm_before

            # Streaming exhaustive oracle
            oracle_top50, layouts_seen = streaming_exhaustive_oracle(
                oracle_store, parent, q["request"], limit=50
            )

            cold_tuples = [(r["world_id"], r["layout_id"], r["score"]) for r in cold_result["results"]]
            warm_tuples = [(r["world_id"], r["layout_id"], r["score"]) for r in warm_result["results"]]
            oracle_tuples = [(r["world_id"], r["layout_id"], r["score"]) for r in oracle_top50]

            if cold_tuples != oracle_tuples:
                raise AssertionError(
                    f"Indexed Cold Top50 differs from streaming oracle for {q['query_type']} "
                    f"side={q['border_side']} mode={q['anchor_mode']}: "
                    f"cold={cold_tuples} != oracle={oracle_tuples}"
                )
            if warm_tuples != oracle_tuples:
                raise AssertionError(
                    f"Indexed Warm Top50 differs from streaming oracle for {q['query_type']} "
                    f"side={q['border_side']} mode={q['anchor_mode']}: "
                    f"warm={warm_tuples} != oracle={oracle_tuples}"
                )

            measurement = {
                "query_id": len(measurements),
                "query_type": q["query_type"],
                "border_side": q["border_side"],
                "anchor_mode": q["anchor_mode"],
                "cold_seconds": cold_seconds,
                "warm_seconds": warm_seconds,
                "cold_stats": cold_result["stats"],
                "warm_stats": warm_result["stats"],
                "layouts_seen": layouts_seen,
                "results_count": len(cold_result["results"]),
                "parity": True,
            }
            measurements.append(measurement)

            progress_update = {
                "stage": "querying",
                "completed_batches": (worlds + batch_size - 1) // batch_size,
                "completed_worlds": worlds,
                "completed_layouts": worlds * 243,
                "current_snapshot_id": parent,
                "source_fixture_identity": info["header"],
                "completed_queries": len(measurements),
                "measurements": measurements,
                "wall_seconds": time.monotonic() - start_time,
            }
            atomic_json(out_path / "progress.json", progress_update)

    queries_seconds = time.monotonic() - queries_start
    total_wall = time.monotonic() - start_time

    report = {
        "schema": "catalog-operational-validation-v1",
        "fabricated": True,
        "fabricated_note": SYNTHETIC_NOTE,
        "worlds": worlds,
        "layouts": worlds * 243,
        "full_layouts": True,
        "snapshot_id": parent,
        "source_coverage_identity": info["header"],
        "audit": audit,
        "info": info,
        "query_parity": True,
        "timings": {
            "total_wall_seconds": total_wall,
            "publication_wall_seconds": publish_seconds,
            "queries_wall_seconds": queries_seconds,
        },
        "latencies": {
            "cold_mean_seconds": statistics.mean(m["cold_seconds"] for m in measurements) if measurements else 0.0,
            "cold_max_seconds": max((m["cold_seconds"] for m in measurements), default=0.0),
            "warm_mean_seconds": statistics.mean(m["warm_seconds"] for m in measurements) if measurements else 0.0,
            "warm_max_seconds": max((m["warm_seconds"] for m in measurements), default=0.0),
        },
        "rows_decoded": sum(m["cold_stats"]["decoded_layouts"] for m in measurements),
        "candidates_evaluated": sum(m["cold_stats"]["eligible_layouts"] for m in measurements),
        "layouts_seen_oracle": sum(m["layouts_seen"] for m in measurements),
        "resources": {
            "process_peak_rss_bytes": get_current_rss_bytes(),
            "catalog_disk_bytes": tree_bytes(catalog_dir),
            "total_output_disk_bytes": tree_bytes(out_path),
        },
        "limits": {
            "max_worlds": 2000,
            "max_bytes": max_bytes,
            "max_rss_bytes": max_rss_bytes,
            "seconds_budget": seconds,
            "batch_size": batch_size,
        },
        "measurements": measurements,
        "explicit_limitations": [
            "Fabricated synthetic operational validation data only; not player demand or natural Minecraft generation.",
            "Single-process harness; parallel HTTP admission/concurrency tested separately by Codex.",
            "SIGKILL retention recovery and process restart survival tested separately by Codex.",
            "No native MC generator or Bedrock BDS execution in this harness.",
        ],
    }

    atomic_json(out_path / "report.json", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New dedicated output root directory")
    parser.add_argument("--worlds", type=int, default=10, help="World count (1..2000)")
    parser.add_argument("--batch-size", type=int, default=5, help="Batch size (1..10)")
    parser.add_argument("--seconds", type=int, default=300, help="Wall clock budget in seconds (1..3600)")
    parser.add_argument("--max-bytes", type=int, default=4 * 1024 * 1024 * 1024, help="Max disk bytes (<=4GiB)")
    parser.add_argument("--max-rss-bytes", type=int, default=4 * 1024 * 1024 * 1024, help="Max peak RSS bytes (<=4GiB)")
    parser.add_argument("--source-root", type=Path, default=None, help="Existing source catalog root (optional)")
    parser.add_argument("--source-snapshot", type=str, default=None, help="Hex64 snapshot in source catalog (optional)")
    args = parser.parse_args()

    report = run(
        output=args.output,
        worlds=args.worlds,
        batch_size=args.batch_size,
        source_root=args.source_root,
        source_snapshot=args.source_snapshot,
        seconds=args.seconds,
        max_bytes=args.max_bytes,
        max_rss_bytes=args.max_rss_bytes,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
