"""Acceptance tests for catalog operational validation harness."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from seed_search.catalog import models
from seed_search.catalog.geometry import anchors
from seed_search.catalog.registry import ENVELOPE, FEATURE_IDS, SIDES, STRUCTURES, BIOMES
from seed_search.catalog.segments import SegmentedCatalog
from seed_search.catalog.service import CatalogService
from seed_search.catalog.summaries import summarize
import catalog_operational_validation as cov


def dir_manifest(directory: Path) -> dict[str, str]:
    """Compute sha256 of all files in directory relative to root."""
    manifest = {}
    for p in sorted(directory.rglob("*")):
        if p.is_file():
            rel = str(p.relative_to(directory))
            manifest[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return manifest


def test_make_fixture_validity_and_243_layouts():
    """Verify synthetic fixture satisfies full schema and summarizes to exactly 243 layouts."""
    obs = cov.make_fixture(42)
    models.validate_observation(obs)

    # Labeled synthetic identity checks
    ident = obs["identity"]
    assert ident["model_id"] == cov.SYNTHETIC_MODEL_ID
    assert ident["game_build_id"] == f"research:{cov.SYNTHETIC_MODEL_ID}"
    assert ident["native_sha256"] == cov.SYNTHETIC_NATIVE_SHA
    assert ident["source_sha256"] == cov.SYNTHETIC_SOURCE_SHA
    assert ident["seed"] == "42"

    # Coverage checks
    assert obs["bounds"] == list(ENVELOPE)
    assert len(obs["structures"]) == 14
    for f in STRUCTURES:
        fid = f["id"]
        assert fid in obs["structures"]
        cov_rec = obs["coverage"][fid]
        assert cov_rec["status"] == "complete"
        assert cov_rec["bounds"] == list(ENVELOPE)
        assert cov_rec["method_id"] == "predictor_viable_starts_v1"

    assert len(obs["biomes"]) == 25600
    assert len(obs["biome_names"]) == 9
    for b in BIOMES:
        bid = b["id"]
        cov_rec = obs["coverage"][bid]
        assert cov_rec["status"] == "complete"
        assert cov_rec["bounds"] == list(ENVELOPE)
        assert cov_rec["method_id"] == "predictor_world_lattice_y63_stride64_v1"

    # Summarize across all 81 anchors x 3 borders = 243 layouts
    summaries = summarize(obs)
    assert len(summaries) == 243
    seen_anchors = {tuple(s["anchor"]) for s in summaries}
    seen_sides = {s["border_side"] for s in summaries}
    assert seen_anchors == set(anchors())
    assert seen_sides == set(SIDES)
    assert len(seen_anchors) == 81
    assert len(seen_sides) == 3


def test_make_fixture_signed_seed_handling():
    """Verify negative and signed 64-bit seeds parse correctly and maintain valid identity."""
    for signed_seed in (-1, -123456789, -(1 << 63), "-987654321"):
        obs = cov.make_fixture(signed_seed)
        models.validate_observation(obs)
        assert obs["identity"]["seed"] == str(signed_seed)
        summaries = summarize(obs)
        assert len(summaries) == 243
        for s in summaries:
            assert s["seed"] == str(signed_seed)


def test_make_fixture_with_template_transforms_and_deduplicates():
    """Verify template transforms structure coordinates, deduplicates, and replaces identity."""
    base = cov.make_fixture(100)
    # Inject duplicate points into base template
    base["structures"]["structure.village"].append(list(base["structures"]["structure.village"][0]))
    base["identity"]["model_id"] = "MC_26_50"
    base["identity"]["game_build_id"] = "research:MC_26_50"

    transformed = cov.make_fixture(200, template=base)
    models.validate_observation(transformed)

    # Engine identity replaced
    assert transformed["identity"]["model_id"] == cov.SYNTHETIC_MODEL_ID
    assert transformed["identity"]["seed"] == "200"

    # Coordinates deduplicated and sorted
    pts = transformed["structures"]["structure.village"]
    assert len(pts) == len(set(tuple(p) for p in pts))
    assert pts == sorted(pts)


def test_parameter_caps_and_validation(tmp_path):
    """Enforce strict parameter bounds and reject invalid boundaries."""
    out_valid = tmp_path / "valid_out"

    # Worlds cap: 1..2000
    with pytest.raises(ValueError, match="worlds must be an integer between 1 and 2000"):
        cov.run(out_valid, worlds=0)
    with pytest.raises(ValueError, match="worlds must be an integer between 1 and 2000"):
        cov.run(out_valid, worlds=2001)

    # Batch size cap: 1..10
    with pytest.raises(ValueError, match="batch_size must be an integer between 1 and 10"):
        cov.run(out_valid, batch_size=0)
    with pytest.raises(ValueError, match="batch_size must be an integer between 1 and 10"):
        cov.run(out_valid, batch_size=11)

    # Seconds cap: 1..3600
    with pytest.raises(ValueError, match="seconds must be an integer between 1 and 3600"):
        cov.run(out_valid, seconds=0)
    with pytest.raises(ValueError, match="seconds must be an integer between 1 and 3600"):
        cov.run(out_valid, seconds=3601)

    # Max bytes cap: <= 4GiB
    with pytest.raises(ValueError, match="max_bytes must be an integer between 1 and 4GiB"):
        cov.run(out_valid, max_bytes=0)
    with pytest.raises(ValueError, match="max_bytes must be an integer between 1 and 4GiB"):
        cov.run(out_valid, max_bytes=5 * 1024 * 1024 * 1024)

    # Existing output directory rejected for initial run
    existing_dir = tmp_path / "already_exists"
    existing_dir.mkdir()
    with pytest.raises(FileExistsError):
        cov.run(existing_dir)

    # Nested or identical source and output rejected
    with pytest.raises(ValueError, match="source_root and output directory cannot be identical or nested"):
        cov.run(out_valid, source_root=out_valid, source_snapshot="a" * 64)


def test_small_operational_run_parity_and_reports(tmp_path):
    """Run real 2-world operational validation, verifying query parity and reports."""
    run_dir = tmp_path / "op_run_2w"
    report = cov.run(run_dir, worlds=2, batch_size=1, seconds=60)

    # Structure of returned report
    assert report["schema"] == "catalog-operational-validation-v1"
    assert report["fabricated"] is True
    assert report["worlds"] == 2
    assert report["layouts"] == 2 * 243
    assert report["full_layouts"] is True
    assert report["query_parity"] is True
    assert "explicit_limitations" in report
    assert len(report["explicit_limitations"]) >= 3

    # Audit validation
    audit = report["audit"]
    assert audit["passed"] is True
    assert audit["worlds"] == 2
    assert audit["layouts"] == 486
    assert audit["snapshot_id"] == report["snapshot_id"]

    # 18 representative queries evaluated (3 borders x 2 modes x 3 types)
    assert len(report["measurements"]) == 18
    for m in report["measurements"]:
        assert m["parity"] is True
        assert m["layouts_seen"] == 486
        assert m["cold_seconds"] >= 0.0
        assert m["warm_seconds"] >= 0.0

    # Ensure progress.json and report.json were saved atomically
    assert (run_dir / "progress.json").is_file()
    assert (run_dir / "report.json").is_file()

    saved_report = json.loads((run_dir / "report.json").read_text())
    assert saved_report == report

    progress = json.loads((run_dir / "progress.json").read_text())
    assert progress["stage"] == "querying"
    assert progress["completed_worlds"] == 2
    assert progress["completed_layouts"] == 486
    assert progress["completed_queries"] == 18


def test_source_root_unchanged_and_isolated(tmp_path):
    """Verify that specifying an existing source catalog leaves source files completely untouched."""
    src_dir = tmp_path / "source_repo"
    out_dir = tmp_path / "isolated_output"

    # Create a minimal 1-world source catalog
    src_obs = cov.make_fixture(1)
    src_sums = summarize(src_obs)
    with SegmentedCatalog(src_dir) as store:
        snap_id = store.publish([src_obs], src_sums)

    # Record digest of all files in source directory
    before_manifest = dir_manifest(src_dir)

    # Run operational harness using source catalog as observation template
    report = cov.run(
        out_dir,
        worlds=2,
        batch_size=1,
        source_root=src_dir,
        source_snapshot=snap_id,
        seconds=60,
    )

    # Verify run succeeded
    assert report["query_parity"] is True
    assert report["worlds"] == 2

    # Verify source directory is completely untouched
    after_manifest = dir_manifest(src_dir)
    assert before_manifest == after_manifest


def test_streaming_oracle_multileaf_dedup(tmp_path):
    """Verify streaming oracle correctly deduplicates world results across leaf boundaries."""
    cat_dir = tmp_path / "multileaf_cat"
    obs1 = cov.make_fixture(10)
    sums1 = summarize(obs1)

    # Publish with leaf_entries=64 so that 243 summaries of world 10 span 4 separate leaf segments
    with SegmentedCatalog(cat_dir, leaf_entries=64, fanout=4) as store:
        snap_id = store.publish([obs1], sums1)
        info = store.info(snap_id)

    service = CatalogService(cat_dir)
    queries = cov.build_representative_queries(snap_id, info["header"])

    with SegmentedCatalog(cat_dir, leaf_entries=64, fanout=4) as oracle_store:
        for q in queries[:6]:
            res = service.query(dict(request=q["request"], page_size=50))
            oracle_top, seen = cov.streaming_exhaustive_oracle(oracle_store, snap_id, q["request"], limit=50)

            service_tuples = [(r["world_id"], r["layout_id"], r["score"]) for r in res["results"]]
            oracle_tuples = [(r["world_id"], r["layout_id"], r["score"]) for r in oracle_top]
            assert service_tuples == oracle_tuples
            assert seen == 243


def test_template_rotation_cannot_escape_half_open_envelope():
    base = cov.make_fixture(1)
    base["structures"]["structure.village"] = [[-5120, -5120], [-5120, 5119]]
    for seed in range(8):
        obs = cov.make_fixture(seed, template=base)
        models.validate_observation(obs)
        assert all(-5120 <= x < 5120 and -5120 <= z < 5120
                   for x, z in obs["structures"]["structure.village"])
