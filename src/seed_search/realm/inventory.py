"""Durable complete scoring inventories and positive witnesses for extra families."""
import fcntl
import os
import time

from ..backend import Backend, STRUCTURES, configure_native_threads, biome_catalog
from .baseline import structure_observation
from .bounds import native_bounds
from .sampling import BiomeSampler, grid_points, dispersed_indices
from .resources import disk_policy, disk_status

NETHER_TYPES = {'fortress', 'bastion', 'ruined_portal_nether'}
END_TYPES = {'end_city'}


def detect_structures(candidate, cfg, backend, *, exhaustive=False):
    if cfg.get('contract')=='master_seed_blueprint_v1':
        from .blueprint import count_observation
        required=dict(candidate['required_structures']);nether={};optional={};observations={};timings={}
        for name,minimum in cfg['structures']['minimum_counts'].items():
            if cfg.get('screening_revision') and name in ('monument','shipwreck'):
                if candidate.get('marine_stage',{}).get('status')=='DEFERRED':continue
                observations[name]=required.get(name,{})
                continue
            if name=='stronghold':
                observations[name]=required[name]
                continue
            started=time.perf_counter()
            required[name]=count_observation(backend,name,candidate['bounds']['overworld'],minimum,capped=False)
            observations[name]=required[name];timings[name]=time.perf_counter()-started
        for name in ('fortress','bastion'):
            nether[name]=count_observation(backend,name,candidate['bounds']['final_nether'],cfg['structures']['nether_minimum_counts'][name],capped=False)
            observations[name]=nether[name]
        if not cfg.get('screening_revision'):
            optional['outpost']=structure_observation(backend,'outpost',candidate['bounds']['overworld'])
            observations['outpost']=optional['outpost']
        else:optional=dict(candidate.get('optional_structures',{}))
        return {'required_structures':required,'required_nether_structures':nether,
                'optional_structures':optional,'structure_inventory':observations,'structure_inventory_seconds':timings}
    bounds = candidate['bounds']['overworld']
    final_nether = candidate['bounds']['final_nether']
    observations = {}
    timings = {}
    required = dict(candidate['required_structures'])
    optional = {}
    pairs = backend.nether_structure_pairs(native_bounds(final_nether)) if hasattr(backend, 'nether_structure_pairs') else None
    for name in STRUCTURES:
        if name == 'stronghold':
            started=time.perf_counter()
            observations[name] = structure_observation(backend,name,bounds) if exhaustive else required[name]
            observations[name] = {**observations[name], 'dimension':'overworld',
                                  'scope':'final border; predictor recall remains incomplete' if exhaustive else 'saved discovery anchor'}
            timings[name]=time.perf_counter()-started
            continue
        area = (cfg.get('discovery', {}).get('overworld_bounds', [-2000, -2000, 2000, 2000]) if name in END_TYPES else
                final_nether if name in NETHER_TYPES else bounds)
        # Presence is sufficient for requirements and once-per-family bonuses.
        # Complete start counts remain an explicit, separately costed audit.
        minimal = not exhaustive and name not in ('fortress', 'bastion')
        started = time.perf_counter()
        observation = structure_observation(backend, name, area, minimal=minimal,
                                            pair=pairs[name] if pairs and name in pairs else None)
        timings[name] = time.perf_counter()-started
        observation['dimension'] = 'end' if name in END_TYPES else 'nether' if name in NETHER_TYPES else 'overworld'
        observation['scope'] = 'supplemental discovery; not Realm eligibility' if name in END_TYPES else 'final border'
        observations[name] = observation
        if name in required:
            required[name] = observation
    for name, bonus in cfg['structures']['optional_bonuses'].items():
        observation = observations.get(name) or structure_observation(backend, name, bounds)
        optional[name] = {**observation, 'bonus': bonus if observation['predicted_viable'] else 0,
                          'bonus_status': 'PREDICTED' if observation['predicted_viable'] else 'unknown; zero observed lower bound'}
        if name not in observations:
            observations[name] = observation
    return {'required_structures': required, 'optional_structures': optional,
            'required_nether_structures': {name: observations[name] for name in ('fortress', 'bastion')},
            'structure_inventory': observations, 'structure_inventory_seconds': timings}


def complete_start_audit(store, cfg, candidate_id):
    """Explicit complete native inventory, independent of the witness queue."""
    from .capabilities import identity
    if store.identity.get('backend') and store.identity['backend'] != identity():
        raise ValueError('Complete-start audit backend identity changed')
    candidate=store.get_candidate(candidate_id)
    if candidate is None:raise ValueError('Unknown candidate')
    begin=time.perf_counter()
    with Backend(candidate['seed']) as backend:
        patch=detect_structures(candidate,cfg,backend,exhaustive=True)
    # A full inventory is an additional revision; it cannot replace the frozen
    # minimal evidence or falsely imply actual-generation completeness.
    observation={'kind':'complete_predictor_start_inventory','candidate_id':candidate_id,
                 'backend':identity(),'structures':patch['structure_inventory'],
                 'seconds':time.perf_counter()-begin,'actual_generation_verified':False}
    store.upsert_observation(candidate_id,observation)
    return observation


def execute_inventory(candidate, cfg, kind, backend, *, exhaustive=False):
    if kind == 'structures':
        return detect_structures(candidate, cfg, backend, exhaustive=exhaustive)
    if kind != 'biomes':
        raise ValueError('Unknown inventory kind')
    if cfg.get('contract')=='master_seed_blueprint_v1':
        from .blueprint import biome_gate
        return {'biomes':biome_gate(backend,candidate['bounds']['overworld'],cfg,complete=True)}
    sampler = BiomeSampler(backend)
    policy = candidate['inventory'].get('sampling_policy', cfg['biomes'])
    # Use the current score weights, retaining the frozen generation/sampling policy.
    policy = {**cfg['biomes'], **policy, 'family_bonuses': cfg['biomes']['family_bonuses'], 'variant_bonuses': cfg['biomes']['variant_bonuses']}
    biomes = sampler.gate(candidate['bounds']['overworld'], policy, complete=True,
                         prior=(candidate.get('biomes') or {}).get('sampling'))
    additional = {}
    for dimension, label, y, spacing, bounds in (
            (-1, 'nether', 33, 64, candidate['bounds']['final_nether']),
            (1, 'end', 63, 128, cfg['discovery']['overworld_bounds'])):
        points = grid_points(bounds, spacing, y, 'world')
        expected=len(points)
        active={item['id'] for item in biome_catalog() if item['generates'] and item['dimension']==dimension}
        if exhaustive:
            values=sampler.sample(points,dimension)
        else:
            sampled=[];ids=[];seen=set()
            order=dispersed_indices(len(points))
            for offset in range(0,len(order),16):
                batch=points[order[offset:offset+16]]
                values=sampler.sample(batch,dimension)
                sampled.extend(batch);ids.extend(map(int,values));seen.update(map(int,values))
                if active<=seen:break
            import numpy as np
            points=np.array(sampled,dtype=np.int32).reshape(-1,3)
            values=np.array(ids,dtype=np.int32)
        from .biomes import postprocess_ids
        item = postprocess_ids(values, points, policy)
        item.update(bounds=list(bounds), sample_y=y, spacing=spacing,
                    sample_count=len(points), expected_grid_points=expected, dimension=label,
                    complete=False, missing_model_ids=sorted(active-set(map(int,values))),
                    detection_method='full_defined_grid' if exhaustive else 'dispersed_positive_class_witnesses',
                    coverage='bounded sample; unseen biomes unresolved, never absent')
        additional[label] = item
    return {'biomes': biomes, 'supplemental_biome_inventories': additional}


def run_inventory(store, cfg, *, limit=None, candidate_id=None, include_pending=False, exhaustive=False, progress=None):
    """One scheduler owns recovery; leases and candidate patches commit together."""
    from .capabilities import identity
    if store.identity.get('backend') and store.identity['backend'] != identity():
        raise ValueError('Inventory backend identity changed; use a fresh compatible run')
    configure_native_threads(cfg['search'].get('native_threads_per_worker', 1))
    if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit < 0):
        raise ValueError('Inventory limit must be nonnegative')
    # Exhaustive supplemental enumeration is an explicit audit, not a resume of
    # a presence-mode task. Use a fresh computation identity for such requests.
    if exhaustive:
        raise ValueError('Use detect_structures(..., exhaustive=True) in an explicit audit; durable inventory uses its frozen presence policy')
    if candidate_id is not None and store.get_candidate(candidate_id) is None:
        raise ValueError('Unknown inventory candidate')
    started = time.monotonic(); cpu = time.process_time(); completed = 0; failed = 0
    lock = (store.run/'inventory-scheduler.lock').open('a+')
    try:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Another inventory scheduler owns this checkpoint') from None
        store.recover_inventory_work()
        while limit is None or completed < limit:
            unit = store.claim_inventory_work(f'inventory-{os.getpid()}', candidate_id, include_pending=include_pending)
            if unit is None:
                break
            try:
                disk_status(store.run, disk_policy(cfg['search']))
                candidate = store.get_candidate(unit['candidate_id'])
                with Backend(candidate['seed']) as backend:
                    patch = execute_inventory(candidate, store.get_state('score_policy') or cfg, unit['kind'], backend)
                store.complete_inventory_work(unit, patch)
                completed += 1
                if progress:
                    progress({'completed_inventory_tasks': completed, 'candidate': candidate['id'], 'kind': unit['kind']})
            except Exception as error:
                store.fail_inventory_work(unit, error)
                failed += 1
                raise
    finally:
        lock.close()
    return {'completed_tasks': completed, 'failed_tasks': failed,
            'seconds': time.monotonic()-started, 'cpu_seconds': time.process_time()-cpu,
            'inventory_work': store.status()['inventory_work']}
