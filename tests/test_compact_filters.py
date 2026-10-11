import copy

import numpy as np
import pytest

from seed_search.backend import Backend, STRUCTURES, sweep_raw
from seed_search.realm.raw import FAMILIES, center_rectangle, nether_center_coverage, dispersed_high32
from seed_search.realm.config import default_config
from seed_search.realm.sampling import BiomeSampler, grid_points, dispersed_indices
from seed_search.realm.baseline import evaluate_seed
from seed_search.realm.store import RealmStore
from seed_search.realm.inventory import execute_inventory,detect_structures


def test_end_batch_preserves_pinned_planar_sampling_and_negative_edges():
    # Frozen pre-optimization End adapter gives 41 here. Overworld's 3D
    # nearest-cell rule would give 42 and must not replace this End rule.
    with Backend(-1) as backend:
        assert backend.biome(-1792,63,-1984,1)==41
        points=grid_points((-2000,-2000,2000,2000),64,63,'world')
        batch=backend.biome_points(points,1)
        scalar=np.array([backend.biome(*map(int,p),1) for p in points])
        assert np.array_equal(batch,scalar)


@pytest.mark.parametrize('seed', [-1, 0, 1, 12345, 2**32-1, -2**63])
def test_structure_witness_and_shared_nether_match_full_predictor(seed):
    with Backend(seed) as backend:
        for name in STRUCTURES:
            if name == 'stronghold':
                continue
            bounds = (-777, -779, 758, 756)
            full = backend.structures(name, bounds)
            first = backend.structure_first(name, bounds)
            assert (first in full) if full else first is None
            if name == 'mineshaft' and full:
                assert first == full[0]
        pairs = backend.nether_structure_pairs((-701, -705, 697, 690))
        for name, (raw, viable) in pairs.items():
            assert sorted(raw) == backend.structures(name, (-701, -705, 697, 690), False)
            assert sorted(viable) == backend.structures(name, (-701, -705, 697, 690), True)


@pytest.mark.parametrize('start', [0, 0x81230000, 2**32-129])
def test_raw_modes_have_exact_declared_contracts(start):
    reference = sweep_raw(start, 129, FAMILIES, mode='reference')
    assert np.array_equal(reference, sweep_raw(start, 129, FAMILIES, mode='complete'))
    assert np.array_equal(np.minimum(reference, 32), sweep_raw(start, 129, FAMILIES, mode='capped'))
    assert np.array_equal(reference > 0, sweep_raw(start, 129, FAMILIES, mode='presence') > 0)


def test_nether_center_area_is_exact_for_single_pair():
    a, b = (-100, -120), (160, 200)
    ra, rb = center_rectangle(a, True), center_rectangle(b, True)
    width = max(0, min(ra[2], rb[2])-max(ra[0], rb[0])+1)
    height = max(0, min(ra[3], rb[3])-max(ra[1], rb[1])+1)
    result = nether_center_coverage([[a], [b]])
    assert result['area'] == width*height
    assert result['fraction'] == width*height/4000**2
    assert nether_center_coverage([[], [b]])['area'] == 0
    assert len(set(dispersed_high32(128))) == 128


def test_world_lattice_preserves_in_border_witness_when_border_grows():
    cfg = default_config()
    policy = cfg['biomes']
    with Backend(7980124511283784280) as backend:
        sampler = BiomeSampler(backend)
        anchor = (772, -1996)
        from seed_search.realm.bounds import square
        before = sampler.gate(square(anchor, 2304), policy, complete=True)
        after = sampler.gate(square(anchor, 2380), policy, complete=True)
        assert set(before['wooded_families']) <= set(after['wooded_families'])
    assert sorted(dispersed_indices(576).tolist()) == list(range(576))


def test_inventory_leases_recover_fence_and_finish_score(tmp_path):
    cfg = default_config()
    cfg['biomes'].update(lattice='border', refinement_budget=0)
    # A naturally qualified saved control; don't depend on a random positive.
    result = evaluate_seed(0, 6506335827835841088, cfg)
    if not any(a['qualification'] == 'PREDICTED' for a in result['anchors']):
        for i in range(32):
            result = evaluate_seed(0, i, cfg)
            if any(a['qualification']=='PREDICTED' for a in result['anchors']):
                break
    candidate = next(a for a in result['anchors'] if a['qualification']=='PREDICTED')
    identity = {'config': cfg}
    with RealmStore(tmp_path/'run', identity) as store:
        store.configure_range(0, 1, 1)
        store.claim_range('baseline')
        store.complete_range(0, 1, [result])
        assert candidate['baseline_score'] is None
        old = store.claim_inventory_work('old', candidate['id'])
        store.recover_inventory_work()
        unit = store.claim_inventory_work('new', candidate['id'])
        with pytest.raises(ValueError, match='Stale'):
            store.complete_inventory_work(old, {})
        with Backend(candidate['seed']) as backend:
            patch = execute_inventory(candidate, cfg, unit['kind'], backend)
        store.complete_inventory_work(unit, patch)
        assert not store.complete_inventory_work(unit, patch)
        unit = store.claim_inventory_work('new', candidate['id'])
        with Backend(candidate['seed']) as backend:
            patch = execute_inventory(store.get_candidate(candidate['id']), cfg, unit['kind'], backend)
        store.complete_inventory_work(unit, patch)
        saved = store.get_candidate(candidate['id'])
        assert saved['baseline_score_complete'] and saved['baseline_score'] is not None
        assert saved['biomes']['sample_count'] == 576
        assert 'buried_treasure' in saved['structure_inventory']
        assert 'end_city' in saved['structure_inventory']
        assert saved['qualification'] == candidate['qualification']
        with Backend(saved['seed']) as backend:
            full=detect_structures(saved,cfg,backend,exhaustive=True)
            from seed_search.realm.bounds import native_bounds
            assert full['structure_inventory']['stronghold']['coordinates']==[
                list(p) for p in backend.structures('stronghold',native_bounds(saved['bounds']['overworld']))]


def test_sampling_rejects_incompatible_saved_lattice():
    policy = default_config()['biomes']
    with Backend(12345) as backend:
        sampler = BiomeSampler(backend)
        result = sampler.gate((-768, -768, 768, 768), policy)
        altered = copy.deepcopy(policy); altered['lattice'] = 'border'
        with pytest.raises(ValueError, match='identity'):
            sampler.gate((-768, -768, 768, 768), altered, complete=True, prior=result['sampling'])
