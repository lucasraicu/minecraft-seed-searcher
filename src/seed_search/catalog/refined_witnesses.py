"""Positive-only refinement over model-matched tiles; coarse misses stay unresolved."""
from .refinement import decode_tile
from .geometry import bounds_for
from .registry import BIOMES
from .codec import MISSING


def model_witnesses(observation,tiles):
    """Recover small-patch witnesses without changing coarse records or counts."""
    points={b['id']:[] for b in BIOMES}
    families={name:b['id'] for b in BIOMES for name in b['canonical_members']}
    for tile in tiles:
        ctx=tile['context']
        if ctx['identity']!=observation['identity'] or ctx['provider']!='procedural_model_v1' or ctx['dimension']!='overworld' or tile['y']!=63:
            continue
        values=decode_tile(tile);x,z,hx,hz=tile['bounds'];names=tile['biome_names']
        for i,raw in enumerate(values):
            if raw is None:continue
            fid=families.get(names.get(str(raw)))
            if fid is not None:points[fid].append([x+i%(hx-x),63,z+i//(hx-x),tile['tile_id']])
    return points


def apply_witnesses(layout,points):
    """Return a scoring copy and explicit witnesses; never invent absence/coverage."""
    import copy
    result=copy.deepcopy(layout);witnesses=[]
    lo_x,lo_z,hi_x,hi_z=bounds_for(layout['anchor'],layout['border_side']);cx,cz=layout['anchor']
    for feature in BIOMES:
        slot=feature['slot'];best=None
        for x,y,z,tile_id in points[feature['id']]:
            if lo_x<=x<hi_x and lo_z<=z<hi_z:
                key=((x-cx)**2+(z-cz)**2,x,z,tile_id)
                if best is None or key<best:best=key
        if best is not None and best[0]<result['biome_nearest_d2'][slot]:
            result['biome_nearest_d2'][slot]=best[0]
            # Keep coarse source references unchanged in persisted summaries.
            # This transient scoring copy's fine witness is served separately.
            result['biome_witness_refs'][slot]=MISSING
            witnesses.append(dict(feature=feature['id'],x=best[1],y=63,z=best[2],tile_id=best[3],distance_squared=best[0],provider='procedural_model_v1'))
    return result,witnesses
