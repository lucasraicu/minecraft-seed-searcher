from seed_search.catalog.models import identity,empty_observation
from seed_search.catalog.refinement import make_tile
from seed_search.catalog.refined_witnesses import model_witnesses,apply_witnesses
from seed_search.catalog.summaries import summarize_at
from seed_search.catalog.codec import MISSING


def test_positive_fine_patch_recovers_without_changing_inventory_or_absence_flags():
    ident=identity(1,model_id='26.50',native_sha256='a'*64,source_sha256='b'*64)
    obs=empty_observation(ident)
    ctx=dict(identity=ident,dimension='overworld',provider='procedural_model_v1',observed_build=None,evidence_sha256='c'*64)
    t=make_tile(ctx,[1,1,3,3],63,[77,1,1,1],biome_names={'77':'mushroom_fields','1':'plains'})
    points=model_witnesses(obs,[t]);assert len(points['biome.mushroom_fields'])==1
    row=summarize_at(obs,[0,0])[0];refined,witnesses=apply_witnesses(row,points)
    from seed_search.catalog.registry import BIOMES
    slot=next(b['slot']for b in BIOMES if b['id']=='biome.mushroom_fields')
    assert row['biome_nearest_d2'][slot]==MISSING and refined['biome_nearest_d2'][slot]==2
    assert row['complete']==refined['complete'] and obs['biomes']==[]
    assert any(w['x']==1 and w['z']==1 for w in witnesses)
    other=dict(ctx,identity=dict(ident,seed='2'))
    assert not any(model_witnesses(obs,[make_tile(other,[1,1,2,2],63,[77],biome_names={'77':'mushroom_fields'})]).values())
