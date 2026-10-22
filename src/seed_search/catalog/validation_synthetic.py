"""Fabricated, explicitly labeled oversubscription corpus; never player seeds."""
from .models import identity,empty_observation,observation_id,world_id
from .registry import BIOMES,STRUCTURES,ENVELOPE,digest
from .codec import layout_id
from .summaries import summarize


def synthetic_snapshot(population=64):
    base=empty_observation(identity(0,model_id='synthetic-validation',native_sha256='0'*64,source_sha256='0'*64))
    for feature in STRUCTURES:
        base['structures'][feature['id']]=[[x,z] for x in (0,64,128) for z in (0,64,128)]
        base['coverage'][feature['id']]={'status':'complete','bounds':list(ENVELOPE),'method_id':'predictor_viable_starts_v1'}
    base['biome_names']={str(i+1):f['canonical_members'][0] for i,f in enumerate(BIOMES)}
    base['biomes']=[[x,63,z,1+(i%9)] for i,(x,z) in enumerate(
        ( (x,z) for x in range(-5120,5120,64) for z in range(-5120,5120,64) ))]
    for feature in BIOMES:
        base['coverage'][feature['id']]={'status':'complete','bounds':list(ENVELOPE),'method_id':'predictor_world_lattice_y63_stride64_v1'}
    templates=[r for r in summarize(base) if r['anchor'] in ([0,0],[256,0],[-256,0])]
    observations=[];layouts=[]
    for seed in range(population):
        obs=dict(base,identity=dict(base['identity'],seed=str(seed)))
        oid=observation_id(obs);wid=world_id(obs['identity']);observations.append(obs)
        for template in templates:
            layouts.append(dict(template,observation_id=oid,world_id=wid,seed=str(seed),
                layout_id=layout_id(oid,template['anchor'],template['border_side'])))
    return {'snapshot_id':digest(['FABRICATED-OVERSUBSCRIPTION-v1',population]),'observations':observations,'layouts':layouts}
