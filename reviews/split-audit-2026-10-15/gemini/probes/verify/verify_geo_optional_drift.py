"""Verification Probe for G-GEO-01 / P1-1:
Optional structure counting boundary drift during snapping between Python and C.

Verification objectives:
1. Verify if synthetic fixture reaches the claimed path in unmodified C (check if w->fixture short-circuits optional structures).
2. Verify Python oracle divergence on synthetic inventory when optional structure falls between unsnapped (cx, cz) and snapped (xx, zz).
3. Test Codex's coordinate regression fixture: seed 123, hut at (56, -800).
4. Verify the minimal recount fix (recounting optional structures at snapped center in Python).
5. Evaluate whether this is an oracle-only bug or affects C.
"""

import sys
from pathlib import Path
sys.path[:0] = [str(Path.cwd()), str(Path.cwd() / 'src'), str(Path.cwd() / 'tests')]

import math
from dataclasses import replace
from seed_search.realm.dynamic import candidate_centers, overworld_bounds, OPTIONAL_NAMES
from seed_search.realm.bounds import contains
from seed_search.realm.blueprint import evaluate_dynamic_seed, dynamic_score
from seed_search.realm.config import dynamic_blueprint_config
from test_dynamic_baseline import DynamicFixtureBackend

def test_c_fixture_short_circuit():
    """Verify that unmodified C short-circuits optional structures when fixture is present."""
    from seed_search.realm.native_batch import Prototype
    p = Prototype('runs/dynamic-baseline-1664/native', dynamic_blueprint_config())
    # Create a fixture sweep using lib
    seeds = p.ffi.new('uint64_t[]', [123])
    fixtures = p.ffi.new('NBFixture[]', [(0, 0, -1, 0, 1)])
    policy = p.ffi.new('NBPolicy *')
    p.ffi.buffer(policy)[:] = bytes(p.ffi.buffer(p.policy))
    policy.retention = 1
    policy.max_misses = 2
    b = p.lib.nb_fixture_sweep(seeds, fixtures, 1, policy, 1)
    assert b != p.ffi.NULL and not b.error
    c = b.results[0].anchors[0]
    
    # Check optional counts in C anchor
    optional_counts = [c.optional[k].viable.n for k in range(5)]
    p.lib.nb_free(b)
    print(f"[C Check] C anchor optional structure counts with fixture: {optional_counts}")
    assert all(cnt == 0 for cnt in optional_counts), "Expected all optional counts to be 0 due to if(w->fixture) return 0;"
    print("  -> CONFIRMED: Unmodified C nb_dynamic_optional short-circuits on w->fixture!")

def test_python_oracle_boundary_drift():
    """Verify that Python candidate_centers evaluates optional structures at unsnapped (cx, cz)
    instead of snapped (xx, zz), causing score and rank divergence."""
    # Test coordinate regression: igloo at (840, 0)
    # A village at (800, 0) pulls the snapped center to (16, 0) or (64, 0).
    # Unsnapped center cx=0: [0-832, 0+832) = [-832, 832). Point 840 is OUTSIDE.
    # Snapped center xx=16: [16-832, 16+832) = [-816, 848). Point 840 is INSIDE.
    inventories = {
        'stronghold': [(0, 0)],
        'mansion': [(0, 0)],
        'village': [(800, 0), (700, 0), (600, 0)],
        'trial_chamber': [(0, 0)],
        'ancient_city': [(0, 0)],
        'desert_pyramid': [(0, 0)],
        'jungle_temple': [(0, 0)],
        'monument': [(0, 0)],
        'ruined_portal': [(0, 0)],
        'shipwreck': [(0, 0)],
        'mineshaft': [(0, 0)],
        'outpost': [(0, 0), (0, 0)],
        'fortress': [(0, 0)],
        'bastion': [(0, 0)],
        'igloo': [(840, 0)],  # Optional: 15 pts
        'swamp_hut': [],
        'trail_ruins': [],
        'ocean_ruin': [],
        'buried_treasure': [],
    }
    floors = {'stronghold': 1, 'mansion': 1, 'monument': 1, 'outpost': 2, 'fortress': 1, 'bastion': 1}
    ideals = {}
    weights = {'village': 1, 'trial_chamber': 1, 'ancient_city': 1, 'desert_pyramid': 1, 'jungle_temple': 1, 'outpost': 1}

    candidates = candidate_centers(inventories, floors, ideals, weights, max_misses=2)
    divergences = []
    for cand in candidates:
        py_igloo = cand.counts.get('igloo', 0)
        c_igloo = sum(contains(p, overworld_bounds(cand.center)) for p in inventories['igloo'])
        if py_igloo != c_igloo:
            divergences.append((cand.center, py_igloo, c_igloo))

    print(f"[Python Check] Total candidate cells: {len(candidates)}, Divergences found: {len(divergences)}")
    assert len(divergences) > 0, "Expected boundary drift divergences!"
    first_div = divergences[0]
    print(f"  -> First divergence at snapped center {first_div[0]}: py_igloo={first_div[1]} vs c_igloo={first_div[2]}")
    print(f"  -> Score discrepancy: {15 * (first_div[2] - first_div[1])} points")

def test_codex_swamp_hut_fixture():
    """Verify Codex's reproduced numerical trigger with swamp hut at (56, -800)."""
    class OptionalFixture(DynamicFixtureBackend):
        def structure_pair(self, name, bounds):
            if name == 'swamp_hut':
                return [(56, -800)], [(56, -800)]
            return super().structure_pair(name, bounds)

    # In unmodified Python:
    res = evaluate_dynamic_seed(0, 123, dynamic_blueprint_config(), backend_factory=lambda _: OptionalFixture())['anchors'][0]
    py_center = res['evaluation_center']
    py_score = res['baseline_score']
    print(f"[Codex Trigger] Unmodified Python selected center: {py_center}, score: {py_score}")
    
    # Notice: In C, (-752, -816) has eastern boundary -752 + 832 = 80, which captures x=56.
    # But in Python, (-784, -816) was selected because at the unsnapped center cx=-784,
    # the eastern boundary was -784 + 832 = 48, which excludes x=56!
    # Let's verify what happens with the minimal recount fix:
    import seed_search.realm.dynamic as d
    orig_candidate_centers = d.candidate_centers

    def recounted_candidate_centers(inventories, *args, **kwargs):
        rows = orig_candidate_centers(inventories, *args, **kwargs)
        fixed_rows = []
        for row in rows:
            bounds = d.overworld_bounds(row.center)
            opt_counts = {n: sum(contains(pt, bounds) for pt in inventories.get(n, ())) for n in d.OPTIONAL_NAMES}
            fixed_rows.append(replace(row, counts={**row.counts, **opt_counts}))
        return fixed_rows

    d.candidate_centers = recounted_candidate_centers
    try:
        fixed_res = evaluate_dynamic_seed(0, 123, dynamic_blueprint_config(), backend_factory=lambda _: OptionalFixture())['anchors'][0]
        recount_center = fixed_res['evaluation_center']
        recount_score = fixed_res['baseline_score']
        print(f"[Codex Trigger] Recounted Python selected center: {recount_center}, score: {recount_score}")
        assert recount_center == [-752, -816] and recount_score == 434, f"Expected [-752, -816], 434 but got {recount_center}, {recount_score}"
        print("  -> CONFIRMED: Recount fix restores selection of [-752, -816] and score 434!")
    finally:
        d.candidate_centers = orig_candidate_centers

if __name__ == '__main__':
    print("=== Running Verification Probe for G-GEO-01 / P1-1 ===")
    test_c_fixture_short_circuit()
    test_python_oracle_boundary_drift()
    test_codex_swamp_hut_fixture()
    print("=== All G-GEO-01 checks PASSED successfully! ===")
