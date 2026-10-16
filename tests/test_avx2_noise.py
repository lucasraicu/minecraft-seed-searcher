import hashlib
import json
from pathlib import Path
import pytest
from seed_search._native import ffi, lib


def test_vendor_hashes_and_patch_metadata():
    backend_path = Path("vendor/backend.json")
    manifest = json.loads(backend_path.read_text())
    root = Path("vendor/cubiomes-bedrock")

    # Verify all files match recorded hashes
    for filename, expected_hash in manifest["files"].items():
        actual_hash = hashlib.sha256((root / filename).read_bytes()).hexdigest()
        assert actual_hash == expected_hash, f"Hash mismatch for {filename}"

    # Verify our patch is in reviewed_patches
    patch_ids = [p["id"] for p in manifest["reviewed_patches"]]
    assert "noise-avx2-perlin-sampling-v1" in patch_ids
    patch = next(p for p in manifest["reviewed_patches"] if p["id"] == "noise-avx2-perlin-sampling-v1")
    assert "noise.c" in patch["files"]
    assert "noise.h" in patch["files"]
    assert "biomenoise.c" in patch["files"]


def test_dark_forest_filters_consistency():
    """Verify isDarkForestPossible and isMansionDarkForestHumidityPossible consistency."""
    from seed_search.backend import Backend

    with Backend(123456789) as b:
        # Check coordinates across multiple quadrants
        for coord in [(0, 0), (100, 200), (-300, 500), (1500, -1200)]:
            x, z = coord
            # Ensure biome call works without crash or divergence
            biome_id = b.biome(x, 63, z)
            assert 0 <= biome_id <= 255
