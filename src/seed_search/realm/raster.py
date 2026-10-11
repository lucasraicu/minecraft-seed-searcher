"""Shared, explicitly graded terrain rasters on a half-open sampling lattice.

Samples describe cells of at most ``resolution`` blocks. Missing values remain
unknown; neither interpolation nor the predictor's sea-level proxy is actual
water evidence. Providers may implement ``sample_raster`` to supply real data.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
import hashlib
import json

import numpy as np


@dataclass
class Raster:
    bounds: tuple[int, int, int, int]
    resolution: int
    height: np.ndarray
    biomes: np.ndarray | None = None
    known: np.ndarray | None = None
    water: np.ndarray | None = None
    natural_ground: np.ndarray | None = None
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if len(self.bounds) != 4 or any(isinstance(v, bool) or int(v) != v for v in self.bounds):
            raise ValueError('Raster bounds must be integer block coordinates')
        self.bounds = tuple(int(v) for v in self.bounds)
        x0, z0, x1, z1 = self.bounds
        if x1 <= x0 or z1 <= z0 or isinstance(self.resolution, bool) or not isinstance(self.resolution, (int, np.integer)) or self.resolution < 1:
            raise ValueError('Raster requires nonempty half-open bounds and positive resolution')
        self.height = np.asarray(self.height, dtype=float)
        expected = ((z1-z0+self.resolution-1)//self.resolution,
                    (x1-x0+self.resolution-1)//self.resolution)
        if self.height.shape != expected:
            raise ValueError(f'Raster shape {self.height.shape} does not match {expected}')
        for name in ('biomes', 'known', 'water', 'natural_ground'):
            value = getattr(self, name)
            if value is not None:
                value = np.asarray(value, dtype=int if name == 'biomes' else bool)
                if value.shape != expected:
                    raise ValueError(f'{name} shape differs from height')
                setattr(self, name, value)
        self.known = np.isfinite(self.height) if self.known is None else self.known & np.isfinite(self.height)
        self.metadata = dict(self.metadata)

    @property
    def shape(self):
        return self.height.shape

    def coordinates(self):
        x0, z0, _, _ = self.bounds
        return np.meshgrid(x0+np.arange(self.shape[1])*self.resolution,
                           z0+np.arange(self.shape[0])*self.resolution)

    def cell_areas(self):
        x0, z0, x1, z1 = self.bounds
        widths = np.minimum(self.resolution, x1-(x0+np.arange(self.shape[1])*self.resolution))
        depths = np.minimum(self.resolution, z1-(z0+np.arange(self.shape[0])*self.resolution))
        return depths[:, None]*widths[None, :]

    def index(self, center):
        x, z = center
        x0, z0, x1, z1 = self.bounds
        if not (x0 <= x < x1 and z0 <= z < z1):
            return None
        return int((z-z0)//self.resolution), int((x-x0)//self.resolution)

    def water_mask(self, sea_level=63):
        """Actual water when supplied; otherwise a labelled prediction only."""
        return self.known & (self.water if self.water is not None else self.height <= sea_level)

    def quality(self):
        if self.metadata.get('unsupported'):
            return 'UNSUPPORTED'
        if self.metadata.get('failed'):
            return 'FAILED'
        if not self.known.all():
            return 'PARTIAL'
        if self.metadata.get('source') != 'actual':
            return 'PREDICTED'
        proven = (self.resolution == 1 and self.water is not None and
                  self.metadata.get('water_evidence') == 'actual_blocks' and
                  self.natural_ground is not None and self.natural_ground.all() and
                  self.metadata.get('natural_ground_evidence') == 'verified_natural')
        return 'VERIFIED' if proven else 'PARTIAL'

    def mask_bounds(self, mask):
        rows, cols = np.nonzero(mask)
        if not len(rows):
            return None
        x0, z0, x1, z1 = self.bounds
        step = self.resolution
        return [x0+int(cols.min())*step, z0+int(rows.min())*step,
                min(x1, x0+(int(cols.max())+1)*step), min(z1, z0+(int(rows.max())+1)*step)]


class RasterCache:
    """Bounded shared cache; provider/edition/settings/channels are identity.

    A provider's ``cache_identity`` must identify its actual build/extraction
    policy. Fallback predictors additionally include an object identity, avoiding
    accidental cross-provider reuse when that declaration is unavailable. Native
    predictions reuse only exact query coordinates in the bounded raster LRU;
    actual raster observations and incomplete/failed provider responses are
    refreshed even for repeated window requests.
    """
    def __init__(self, maximum_entries=32):
        if maximum_entries < 1:
            raise ValueError('Cache requires at least one entry')
        self.maximum_entries = maximum_entries
        self.entries = OrderedDict()
        self.hits = self.misses = 0
        self.reused_points = self.queried_points = 0
        self.scopes = {}
        self.sampling_axes = {}

    def sample(self, provider, seed, bounds, resolution, *, stage='height', dimension='overworld', settings=None):
        settings = settings or {}
        identity = getattr(provider, 'cache_identity', None)
        if callable(identity):
            identity = identity()
        identity = identity or {'class': type(provider).__qualname__, 'instance': id(provider)}
        fallback = not hasattr(provider, 'sample_raster')
        if fallback and hasattr(provider, 'seed') and str(provider.seed) != str(seed):
            raise ValueError('Predictor seed differs from requested cache seed')
        scope = hashlib.sha256(json.dumps([str(seed), identity, settings, dimension, stage, 'fallback_native' if fallback else 'provider_raster'], sort_keys=True, default=str).encode()).hexdigest()
        payload = [str(seed), identity, settings, dimension, tuple(bounds), int(resolution), stage, 'fallback_native' if fallback else 'provider_raster']
        key = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
        cached = self.entries.get(key)
        # Missing/failed actual responses may omit the source tag. Let their
        # provider retry/review its own evidence rather than adding a stale
        # exact-window cache layer. Native predictions remain deterministic,
        # including unknown cells, and can still reuse their bounded payloads.
        if cached is not None and cached.metadata.get('source') != 'actual' and (fallback or cached.quality() == 'PREDICTED'):
            self.hits += 1
            result = self.entries.pop(key)
            self.entries[key] = result
            return result
        self.misses += 1
        if hasattr(provider, 'sample_raster'):
            result = provider.sample_raster(seed=str(seed), bounds=tuple(bounds), resolution=resolution,
                                            stage=stage, dimension=dimension, settings=settings)
            if isinstance(result, dict):
                result = Raster(**result)
            if not isinstance(result, Raster):
                raise TypeError('Provider sample_raster must return Raster or its constructor fields')
            if result.bounds != tuple(bounds) or result.resolution != resolution:
                raise ValueError('Provider returned a different sampling lattice')
        else:
            if dimension != 'overworld':
                raise ValueError('Fallback terrain predictor only supports Overworld')
            axes = _sampling_axes(bounds, resolution)
            previous = [(value, self.sampling_axes[entry]) for entry, value in reversed(self.entries.items())
                        if self.scopes.get(entry) == scope and entry in self.sampling_axes and value.metadata.get('source') == 'prediction']
            result = _predictor_sample(provider, bounds, resolution, stage, previous=previous, axes=axes)
            self.sampling_axes[key] = axes
            self.reused_points += result.metadata['sampling_reuse']['exact_points_reused']
            self.queried_points += result.metadata['sampling_reuse']['points_queried']
        self.entries[key] = result
        self.scopes[key] = scope
        while len(self.entries) > self.maximum_entries:
            removed, _ = self.entries.popitem(last=False)
            self.scopes.pop(removed, None)
            self.sampling_axes.pop(removed, None)
        return result


def _sampling_axes(bounds, resolution):
    """The actual integer coordinates passed to the native predictor, never rounded neighbors."""
    if len(bounds) != 4 or any(isinstance(v, bool) or int(v) != v for v in bounds):
        raise ValueError('Predictor raster bounds require integer block coordinates')
    if isinstance(resolution, bool) or not isinstance(resolution, (int, np.integer)) or resolution < 1:
        raise ValueError('Predictor resolution must be a positive integer')
    x0, z0, x1, z1 = map(int, bounds)
    if x0 >= x1 or z0 >= z1:
        raise ValueError('Predictor bounds must be nonempty half-open rectangles')
    return (np.arange(x0, x1, resolution, dtype=np.int32),
            np.arange(z0, z1, resolution, dtype=np.int32))


def _predictor_sample(provider, bounds, resolution, stage, *, previous=(), axes=None):
    """Copy only identical native-query coordinates; compute all remaining cells.

    Arrays and Cartesian lattice intersections keep memory proportional to the
    bounded raster payloads. No per-point dictionary or spatial interpolation is
    used. Prediction heights/biomes are deterministic; actual providers bypass
    this path so evolving fluids and coverage are never point-reused.
    """
    if stage not in {'nomination', 'height'}:
        raise ValueError('Unknown raster stage')
    xs, zs = axes if axes is not None else _sampling_axes(bounds, resolution)
    shape = (len(zs), len(xs))
    height = np.full(shape, np.nan)
    biome = np.zeros(shape, dtype=np.int32)
    filled = np.zeros(shape, bool)
    for cached, (old_xs, old_zs) in previous:
        _, target_cols, source_cols = np.intersect1d(xs, old_xs, assume_unique=True, return_indices=True)
        if not len(target_cols):
            continue
        _, target_rows, source_rows = np.intersect1d(zs, old_zs, assume_unique=True, return_indices=True)
        if not len(target_rows):
            continue
        target = np.ix_(target_rows, target_cols)
        source = np.ix_(source_rows, source_cols)
        already_filled = filled[target]
        height[target] = np.where(already_filled, height[target], cached.height[source])
        biome[target] = np.where(already_filled, biome[target], cached.biomes[source])
        filled[target] = True
        if filled.all():
            break
    reused = int(filled.sum())
    if stage == 'nomination' and not reused:
        row_batch = max(1, 100_000//len(xs))
        for start in range(0, len(zs), row_batch):
            count = min(row_batch, len(zs)-start)
            sampled = provider.grid(int(xs[0]), int(zs[start]), len(xs), count, resolution)
            height[start:start+count] = sampled['approx_height']
            biome[start:start+count] = sampled['biomes']
    elif stage == 'nomination':
        # Climate/approximate height remain inexpensive 2D hints, queried as
        # contiguous missing row runs so density heights never replace 2D data.
        for row in range(len(zs)):
            missing = ~filled[row]
            edges = np.diff(np.r_[False, missing, False].astype(np.int8))
            for first, end in zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)):
                for start in range(int(first), int(end), 100_000):
                    stop = min(start+100_000, int(end))
                    sampled = provider.grid(int(xs[start]), int(zs[row]), stop-start, 1, resolution)
                    height[row, start:stop] = np.asarray(sampled['approx_height']).reshape(-1)
                    biome[row, start:stop] = np.asarray(sampled['biomes']).reshape(-1)
    else:
        missing = np.flatnonzero(~filled)
        for start in range(0, len(missing), 100_000):
            indices = missing[start:start+100_000]
            rows, cols = indices//len(xs), indices%len(xs)
            points = np.column_stack((xs[cols], zs[rows]))
            h, b = provider.heights(points, 8)
            height.ravel()[indices] = h
            biome.ravel()[indices] = b
    return Raster(tuple(bounds), resolution, height, biome,
                  metadata={'source': 'prediction', 'provider': 'MC_26_50 density predictor',
                            'target': 'Bedrock 26.52; not an exact-version generator',
                            'stage': stage, 'water_evidence': 'height_at_or_below_sea_level_proxy',
                            'natural_ground_evidence': 'raw_density_prediction',
                            'sampling_reuse': {'exact_points_reused': reused, 'points_queried': height.size-reused},
                            'limitations': ['No actual fluid, aquifer, cave, decoration or structure ground proof',
                                            'Sampling can miss narrow land/water connections']})
