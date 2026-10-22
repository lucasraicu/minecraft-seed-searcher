"""Immutable, version-bound query view built from a fully verified snapshot."""
from dataclasses import dataclass
from types import MappingProxyType
from .models import validate_observation, observation_id, world_id
from .codec import validate_summary, pack_summary, unpack_summary, summary_metadata
from .registry import digest, POLICY, REGISTRY_REVISION
from .request import validate_request, load_request
from .query import _rank


def _freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({k:_freeze(v) for k,v in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(v) for v in value)
    return value


@dataclass(frozen=True, slots=True, init=False)
class SnapshotView:
    snapshot_id: str
    registry_revision: str
    policy_sha256: str
    _header: object
    _layouts: tuple
    world_ids: frozenset

    @classmethod
    def from_snapshot(cls, data):
        """Call after CatalogStore.snapshot verified disk checksums and membership.

        Revalidates raw records once, then keeps only immutable layout facts and
        pinned build/settings metadata. No caller-owned mutable arrays survive.
        """
        if not isinstance(data, dict) or set(data) != {'snapshot_id','observations','layouts'}:
            raise ValueError('Invalid verified snapshot input')
        if not isinstance(data['snapshot_id'],str) or not data['snapshot_id']:
            raise ValueError('Missing snapshot identity')
        obs_by_id={}; headers=set(); worlds=set()
        for obs in data['observations']:
            validate_observation(obs); ident=obs['identity']; oid=observation_id(obs)
            if oid in obs_by_id or world_id(ident) in worlds:
                raise ValueError('Duplicate world/observation')
            obs_by_id[oid]=ident; worlds.add(world_id(ident))
            headers.add(tuple((k,v) for k,v in sorted(ident.items()) if k!='seed'))
        if len(headers)!=1:
            raise ValueError('Snapshot must have one compatible build/settings identity')
        frozen=[]; layout_ids=set()
        for layout in data['layouts']:
            validate_summary(layout)
            ident=obs_by_id.get(layout['observation_id'])
            if ident is None or layout['world_id']!=world_id(ident) or layout['seed']!=ident['seed']:
                raise ValueError('Layout/observation identity mismatch')
            if layout['layout_id'] in layout_ids: raise ValueError('Duplicate layout')
            layout_ids.add(layout['layout_id'])
            # Pack/unpack produces a defensive canonical copy with validated types.
            frozen.append(_freeze(unpack_summary(pack_summary(layout),summary_metadata(layout))))
        result=object.__new__(cls)
        for name,value in dict(snapshot_id=data['snapshot_id'],registry_revision=REGISTRY_REVISION,
            policy_sha256=digest(POLICY),_header=MappingProxyType(dict(next(iter(headers)))),
            _layouts=tuple(frozen),world_ids=frozenset(worlds)).items():
            object.__setattr__(result,name,value)
        return result

    def search(self, request, *, limit=5, world_ids=None):
        if type(limit) is not int or not 1<=limit<=50: raise ValueError('Result limit must be1..50')
        if self.policy_sha256!=digest(POLICY) or self.registry_revision!=REGISTRY_REVISION:
            raise ValueError('Stale snapshot view policy/registry')
        expected={'snapshot_id':self.snapshot_id,'game_build_id':self._header['game_build_id'],
                  'world_settings_id':self._header['world_settings_id']}
        req=load_request(request,**expected) if isinstance(request,str) else validate_request(request,**expected)
        selected=self.world_ids if world_ids is None else frozenset(world_ids)
        if not selected<=self.world_ids: raise ValueError('Unknown selected world')
        layouts=(layout for layout in self._layouts if layout['world_id'] in selected)
        return _rank(layouts,req,limit,validate_records=False)
