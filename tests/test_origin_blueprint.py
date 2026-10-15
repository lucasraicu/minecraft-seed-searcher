"""Origin policy must preserve exact eligibility and distinguish center from Strongholds."""
import copy
import csv
from pathlib import Path

import pytest

from seed_search.realm.blueprint import smart_score
from seed_search.realm.blueprint import evaluate_seed
from seed_search.realm.config import (ORIGIN_REVISION, origin_blueprint_config,
                                      outpost_blueprint_config, validate_config)
from seed_search.realm.native_batch import Prototype, semantic_record
from scripts.build_blueprint_batch import build
from seed_search.realm.store import RealmStore

ROOT=Path(__file__).parents[1]
@pytest.fixture(scope='module')
def prototype(tmp_path_factory):
    directory=tmp_path_factory.mktemp('origin-native')
    prefix=ROOT/'runs/master-implementation-2026-10-10/openmp/install'
    build(directory,prefix if (prefix/'include/omp.h').exists() else None)
    return Prototype(directory,origin_blueprint_config())


def test_versioned_fixed_policy_and_historical_control():
    cfg=origin_blueprint_config();validate_config(cfg)
    assert cfg['screening_revision']==ORIGIN_REVISION
    assert cfg['discovery']['overworld_bounds']==[-1024,-1024,1024,1024]
    assert cfg['discovery']['nether_bounds']==[-512,-512,512,512]
    assert cfg['terrain']['v1']['coastal_continent']['river_highway_bonus_points']==35
    old=outpost_blueprint_config();validate_config(old)
    assert old['discovery']['overworld_bounds']==[-2000,-2000,2000,2000]
    assert old['terrain']['v1']['coastal_continent']['river_highway_bonus_points']==20
    wrong=copy.deepcopy(cfg);wrong['discovery']['overworld_bounds']=[-2000,-2000,2000,2000]
    with pytest.raises(ValueError):validate_config(wrong)


def test_origin_positive_misses_and_mandatory_stronghold(prototype):
    fixtures=[(0,0,-1),(0,0,12),(0,0,-1),(0,0,28)]
    masks=[0,0,(1<<12)|(1<<2),0]
    with prototype.sweep([0,1,2,3],fixtures=fixtures,fixture_masks=masks,
                         retention='survivors',max_misses=1) as batch:
        assert batch.pointer.result_count==2
        rows=batch.retained_records()
        assert [r['index'] for r in rows]==[0,1]
        perfect,miss=(r['anchors'][0] for r in rows)
        assert perfect['stronghold']==[0,0]
        assert perfect['evaluation_center']==[0,0]
        assert perfect['required_structures']['stronghold']['predicted_viable']==[[16,0],[32,0]]
        assert perfect['ranking']['bonuses']['stronghold']==50
        assert perfect['qualification']=='PREDICTED'
        assert miss['pending_reasons']==['count_outpost']
        assert miss['retention']['classification']=='NEAR_MISS'
        receipt=batch.retention_receipt()
        assert receipt['inputs']==4 and receipt['retained_inputs']==2
    with prototype.sweep([0,3],fixtures=[fixtures[0],fixtures[3]],complete=True) as batch:
        direct=batch.records();replay=batch.records(adapter='replay')
        assert [semantic_record(r) for r in direct]==[semantic_record(r) for r in replay]
        assert direct[1]['anchors'][0]['pending_reasons'][0]=='count_stronghold'


def test_origin_jackpot_values():
    def obs(n):return {'predicted_viable':[[i,0] for i in range(n)]}
    structures={k:obs(v) for k,v in {'stronghold':2,'mansion':2,'village':8,
        'ancient_city':4,'desert_pyramid':2,'jungle_temple':2,'ruined_portal':6,
        'trial_chamber':5,'mineshaft':15,'outpost':4}.items()}
    nether={'fortress':obs(4),'bastion':obs(5)}
    optional={'monument':obs(2)}
    score=smart_score(structures,nether,optional,locked=True,river=True,origin=True,
                      biome_names=['cherry_grove','badlands','wooded_badlands','mushroom_fields'],
                      metrics={'river_highway_connected':True})['bonuses']
    assert {k:score[k] for k in ('stronghold','mansion','river_highway','ancient_city',
        'fortress','bastion','monument','village','outpost','desert_pyramid',
        'jungle_temple','cherry_grove','badlands','mushroom_fields')}=={
        'stronghold':50,'mansion':50,'river_highway':35,'ancient_city':50,
        'fortress':40,'bastion':40,'monument':30,'village':10,'outpost':20,
        'desert_pyramid':10,'jungle_temple':10,'cherry_grove':15,'badlands':15,
        'mushroom_fields':15}


def test_origin_compact_durable_retry_and_task_tables(prototype,tmp_path):
    with prototype.sweep([0,1,2],fixtures=[(0,0,-1),(0,0,12),(0,0,28)],
                         retention='survivors',max_misses=1) as batch:
        records=batch.retained_records()
        receipt=batch.retention_receipt()
    with RealmStore(tmp_path,{'config':prototype.cfg,'retention':{'mode':'survivors','max_misses':1}}) as store:
        store.configure_range(0,3,3)
        assert store.claim_range('origin-test')==(0,3)
        prepared=store.prepare_retained_range(0,3,records,receipt)
        assert store.complete_prepared(prepared,lease=('origin-test',1))
        assert not store.complete_prepared(prepared)
        assert store.status()['saved_seed_rows']==2
        assert store.db.execute('SELECT count(*) FROM variant_tasks').fetchone()[0]==2
        assert store.db.execute('SELECT count(*) FROM discovery_tasks').fetchone()[0]==4
        assert store.db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        from seed_search.realm.reports import export
        export(store)
        csv.field_size_limit(10 << 20)
        with (tmp_path/'results'/'current'/'baseline.csv').open() as handle:
            rows=list(csv.DictReader(handle))
        assert len(rows)==2
        assert rows[0]['stronghold']=='[16, 0]'
        assert rows[0]['evaluation_center']=='[0, 0]'
        assert rows[0]['predicted_strongholds']=='[[16, 0], [32, 0]]'
    with RealmStore(tmp_path,resume=True) as store:
        assert store.status()['completed_seeds']==3
        assert store.claim_range('resume') is None


@pytest.mark.parametrize('complete',[False,True])
def test_real_origin_native_replay_python_agree(prototype,complete):
    seeds=[0,-1,-2**63,2**63-1,12345,2**32+12345]
    cfg=prototype.cfg
    with prototype.sweep(seeds,threads=2 if prototype.identity['openmp'] else 1,
                         complete=complete) as batch:
        direct=batch.records()
        replay=batch.records(adapter='replay')
    assert [semantic_record(r) for r in direct]==[semantic_record(r) for r in replay]
    for i,(seed,row) in enumerate(zip(seeds,direct)):
        independent=evaluate_seed(i,seed,cfg,short_circuit=not complete)
        assert semantic_record(row)==semantic_record(independent)
        assert len(row['anchors'])==1 and row['anchors'][0]['stronghold']==[0,0]
