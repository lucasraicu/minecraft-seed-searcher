"""Deterministic biome witnesses; canonical inventory and supplemental evidence differ."""
import math

import numpy as np

from ..backend import biome_name
from .biomes import WOOD, canonical, postprocess_ids, classify
from .bounds import contains


def grid_points(bounds, spacing, y, lattice='world'):
    if lattice not in ('border', 'world'):
        raise ValueError('Unknown biome lattice')
    x0, z0, x1, z1 = bounds
    if lattice == 'world':
        x0 = math.ceil(x0/spacing)*spacing
        z0 = math.ceil(z0/spacing)*spacing
    x, z = np.meshgrid(np.arange(x0, x1, spacing, dtype=np.int32),
                       np.arange(z0, z1, spacing, dtype=np.int32))
    return np.ascontiguousarray(np.column_stack((x.ravel(), np.full(x.size, y), z.ravel())), dtype=np.int32)


def dispersed_indices(n):
    if not n:
        return np.array([], dtype=np.int32)
    stride = max(1, int(n*.618033988749895))
    while math.gcd(stride, n) != 1:
        stride += 1
    return (np.arange(n, dtype=np.int64)*stride % n).astype(np.int32)


def wooded_ids(values):
    names = {canonical(biome_name(int(i))) for i in values}
    return {family for family, members in WOOD.items() if names.intersection(members)}


class BiomeSampler:
    """Full-seed, context-local cache. No high32 sibling reuse or leaf hints."""
    def __init__(self, backend, maximum=65536):
        self.backend = backend
        self.maximum = maximum
        self.cache = {}
        self.queried = 0
        self.hits = 0

    def sample(self, points, dimension=0):
        missing = list(dict.fromkeys((dimension, *map(int, p)) for p in points
                                    if (dimension, *map(int, p)) not in self.cache))
        fetched = {}
        for offset in range(0, len(missing), 100000):
            batch = missing[offset:offset+100000]
            xyz = np.array([p[1:] for p in batch], dtype=np.int32)
            values = self.backend.biome_points(xyz) if dimension == 0 else self.backend.biome_points(xyz, dimension)
            if len(values) != len(batch):
                raise ValueError('Biome provider returned an incomplete sample batch')
            fetched.update(zip(batch, map(int, values)))
        self.queried += len(missing)
        self.hits += len(points)-len(missing)
        values = np.array([fetched.get((dimension, *map(int, p)),
                           self.cache.get((dimension, *map(int, p)))) for p in points], dtype=np.int32)
        self.cache.update(fetched)
        # Bounded lifetime and memory. Witnesses already emitted into candidate
        # records remain available even when cache entries are evicted.
        while len(self.cache) > self.maximum:
            self.cache.pop(next(iter(self.cache)))
        return values

    def gate(self, bounds, policy, *, complete=False, prior=None):
        step = policy['spacing']; y = policy['sample_y']
        lattice = policy.get('lattice', 'world')
        points = grid_points(bounds, step, y, lattice)
        if prior and any(prior.get(k) != v for k, v in
                         (('version', 'biome-lattice-v2'), ('lattice', lattice), ('spacing', step), ('y', y), ('expected_points', len(points)))):
            raise ValueError('Saved biome sampling identity differs')
        saved = {int(row['index']): int(row['id']) for row in (prior or {}).get('canonical_samples', [])}
        for i, value in saved.items():
            if not 0 <= i < len(points):
                raise ValueError('Saved sample index outside canonical lattice')
            self.cache[(0, *map(int, points[i]))] = value
        supplemental = {(tuple(row['coordinate']), int(row['id']))
                        for row in (prior or {}).get('supplemental_samples', [])
                        if contains((row['coordinate'][0], row['coordinate'][2]), bounds)}
        if lattice == 'world':
            canonical_coords = set(map(tuple, points.tolist()))
            for (dimension, x, py, z), value in self.cache.items():
                if dimension == 0 and py == y and contains((x, z), bounds) and (x, py, z) not in canonical_coords:
                    if wooded_ids([value]):
                        supplemental.add(((x, py, z), value))
        indices = np.arange(len(points), dtype=np.int32) if complete else dispersed_indices(len(points))
        families = wooded_ids([*saved.values(), *(v for p, v in supplemental)])
        for offset in range(0, len(indices), 100000 if complete else policy.get('gate_batch_size', 16)):
            if not complete and len(families) >= 2:
                break
            selected = [int(i) for i in indices[offset:offset+(100000 if complete else policy.get('gate_batch_size', 16))] if int(i) not in saved]
            if not selected:
                continue
            values = self.sample(points[selected])
            saved.update(zip(selected, map(int, values)))
            families.update(wooded_ids(values))
        if not complete and len(families) < 2 and lattice == 'world' and policy.get('refinement_budget', 128):
            finer = grid_points(bounds, max(4, step//2), y, 'world')
            known = set(map(tuple, points.tolist())) | {p for p, v in supplemental}
            finer = np.array([p for p in finer[dispersed_indices(len(finer))] if tuple(p) not in known], dtype=np.int32).reshape(-1, 3)
            budget = min(len(finer), policy.get('refinement_budget', 128))
            for offset in range(0, budget, 16):
                batch = finer[offset:min(offset+16, budget)]
                values = self.sample(batch)
                supplemental.update((tuple(map(int, p)), int(v)) for p, v in zip(batch, values))
                families.update(wooded_ids(values))
                if len(families) >= 2:
                    break
        ordered = sorted(saved)
        result = postprocess_ids(np.array([saved[i] for i in ordered], dtype=np.int32), points[ordered], policy)
        if supplemental:
            # Supplemental positives affect presence, never canonical frequency.
            extras = classify([*result['raw_names'], *(biome_name(v) for p, v in supplemental)], policy)
            detections = result['raw_detections']
            result.update(extras)
            result['raw_detections'] = detections
        result.update(bounds=list(bounds), spacing=step, sample_y=y, sample_count=len(saved),
                      data_status='PREDICTED', source='MC_26_50 fixed-Y biome prediction; not exact surface generation',
                      inventory_status='COMPLETE' if len(saved) == len(points) else 'DEFERRED',
                      sampling={'version': 'biome-lattice-v2', 'lattice': lattice, 'spacing': step, 'y': y,
                                'expected_points': len(points), 'canonical_samples': [{'index': i, 'id': saved[i]} for i in ordered],
                                'supplemental_samples': [{'coordinate': list(p), 'id': v} for p, v in sorted(supplemental)],
                                'frequency_domain': 'canonical lattice only', 'order': 'dispersed-coprime-v1'})
        result['witnesses'] = [{'coordinate': points[i].tolist(), 'id': saved[i], 'biome': biome_name(saved[i])}
                               for i in ordered if wooded_ids([saved[i]])]
        result['witnesses'] += [{'coordinate': list(p), 'id': v, 'biome': biome_name(v), 'supplemental': True}
                                for p, v in sorted(supplemental) if wooded_ids([v])]
        return result
