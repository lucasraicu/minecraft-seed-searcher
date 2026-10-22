"""Independent whole-population sort oracle and deliberately oversubscribed facts."""
import copy
import random
import pytest
from seed_search.catalog.models import identity,world_id
from seed_search.catalog.codec import layout_id,MISSING
from seed_search.catalog.registry import digest,STRUCTURES,BIOMES,SIDES,POLICY
from seed_search.catalog.retention import retain,merge,DEFAULT_CAPACITIES
from seed_search.catalog.retention_oracle import oracle_memberships,objective_ids


def facts(seed,cell=255,anchor=(0,0),side=2048):
    ident=identity(seed,model_id='synthetic',native_sha256='a'*64,source_sha256='b'*64)
    oid=digest(['synthetic',seed]);counts=[[1,2,3,4] for _ in range(14)];bs=[10000]*9
    for bit,fid in enumerate(POLICY['retention']['diversity']['bits']):
        enabled=bool(cell&(1<<bit))
        if fid.startswith('biome.'):
            slot=next(f['slot'] for f in BIOMES if f['id']==fid)
            bs[slot]=10000 if enabled else MISSING
        else:
            slot=next(f['slot'] for f in STRUCTURES if f['id']==fid)
            counts[slot]=[1,2,3,4] if enabled else [0]*4
    row=dict(revision='catalog-summary-v1',observation_id=oid,world_id=world_id(ident),
        layout_id=layout_id(oid,anchor,side),seed=str(seed),anchor=list(anchor),border_side=side,
        counts=counts,structure_nearest_d2=[10000 if r[0] else MISSING for r in counts],
        biome_nearest_d2=bs,biome_witness_refs=[MISSING]*9,complete=[[True]*4 for _ in range(23)])
    from seed_search.catalog.models import SUMMARY_REVISION
    row['revision']=SUMMARY_REVISION
    return ident,row


def test_all_diversity_cells_and_objective_families_oversubscribed():
    identities=[];layouts=[]
    # Three distinct worlds for each exact cell. Every one of 6,931 objectives
    # has >K candidates at K1, including ALL 6,144 diversity objectives.
    for cell in range(256):
        for copy_index in range(3):
            seed=cell*3+copy_index
            for side in SIDES:
                ident,row=facts(seed,cell,side=side);layouts.append(row)
            identities.append(ident)
    caps={k:1 for k in DEFAULT_CAPACITIES}
    actual=retain(layouts,identities,capacities=caps)
    expected=oracle_memberships(layouts,identities,caps)
    assert set(actual['objectives'])==set(objective_ids())
    assert actual['objectives']==expected['objectives']
    assert actual['world_ids']==expected['world_ids']
    assert all(len(members)==1 for members in actual['objectives'].values())


def test_partial_coverage_multianchor_unsigned_ties_and_overlap_merge():
    identities=[];layouts=[];rng=random.Random(720720)
    for seed in (0,1,-1,-(1<<63),(1<<63)-1,24,79):
        for anchor in ((0,0),(256,0),(-256,0)):
            ident,row=facts(seed,anchor=anchor)
            row['counts'][0]=sorted(rng.randrange(17) for _ in range(4))
            if seed==24:row['complete'][0]=[False]*4
            if seed==79:row['complete'][14]=[False]*4
            layouts.append(row)
        identities.append(ident)
    caps={k:min(2,v) for k,v in DEFAULT_CAPACITIES.items()}
    actual=retain(layouts,identities,capacities=caps,pins=[world_id(identities[-1])])
    expected=oracle_memberships(layouts,identities,caps,pins=actual['pins'])
    assert actual['objectives']==expected['objectives']
    assert actual['world_ids']==expected['world_ids']
    # Partition by anchors, so one world can win with different layouts in
    # different partitions. The merge must choose its globally best layout.
    parts=[retain(layouts[i::3],identities,capacities=caps,pins=actual['pins']) for i in range(3)]
    assert merge(parts)==actual
    assert merge(list(reversed(parts)))==actual
    changed=copy.deepcopy(parts[0]);changed['build_revision']='0'*64
    with pytest.raises(ValueError,match='build_revision'):merge([parts[0],changed])
    incompatible=copy.deepcopy(identities);incompatible[-1]['native_sha256']='c'*64
    with pytest.raises(ValueError,match='Mixed'):retain(layouts,incompatible)


def test_merge_rejects_same_layout_rank_corruption_and_missing_objective():
    ident,row=facts(5);a=retain([row],[ident]);b=copy.deepcopy(a)
    oid='structure_count:structure.village:0:2048:origin'
    b['objectives'][oid][0]['rank'][0]=-999
    with pytest.raises(ValueError,match='Conflicting rank/layout'):merge([a,b])
    b=copy.deepcopy(a);b['objectives'].pop(oid)
    with pytest.raises(ValueError,match='objective'):merge([a,b])
