"""Review regressions: latest geometry, scores, ranking and honest web evidence."""
import io
import json
import sqlite3
from pathlib import Path
from fractions import Fraction

import pytest

from seed_search.realm.blueprint import dynamic_score
from seed_search.realm.config import dynamic_blueprint_config
from seed_search.realm.dynamic import candidate_centers, nether_bounds, hub_bonus
from seed_search.realm import leaderboard
from seed_search.web import server


def test_scores_named_ordinals_and_repeating_scalers():
    counts={'mansion':2,'stronghold':2,'monument':2,'ancient_city':4,
            'village':9,'trial_chamber':8,'desert_pyramid':3,'jungle_temple':3,
            'outpost':3,'fortress':3,'bastion':3,'shipwreck':7,'ruined_portal':8,'mineshaft':16}
    assert dynamic_score(counts,[])==301
    higher={**counts,**{n:20 for n in ('mansion','stronghold','monument','ancient_city','desert_pyramid','jungle_temple','outpost','fortress','bastion')}}
    assert dynamic_score(higher,[])==301
    assert dynamic_score({'swamp_hut':2,'igloo':1,'trail_ruins':1,'ocean_ruin':1,'buried_treasure':1},[])==58
    assert dynamic_score({},['warm_ocean','ice_spikes','windswept_savanna','shattered_savanna'])==45


def test_hub_bonus_boundary_and_cap():
    assert hub_bonus({'village':[(512,0),(513,0)],'ruined_portal':[(0,512)]},(0,0))==10
    assert hub_bonus({'village':[(0,0)]*100},(0,0))==40


def test_default_yaml_and_web_metadata_are_generated_from_policy():
    import yaml
    from scripts.export_web_policy import profiles
    cfg=dynamic_blueprint_config()
    assert yaml.safe_load(Path('config/realm.yaml').read_text())==cfg
    assert yaml.safe_load(Path('config/realm_1664.yaml').read_text())==cfg
    assert json.loads(Path('web-ui/src/constants/searchProfiles.json').read_text())==profiles()


def test_dynamic_leaderboard_uses_deficits_score_radial_origin():
    db=sqlite3.connect(':memory:')
    db.executescript('CREATE TABLE candidates(id TEXT,idx INTEGER,seed TEXT,qualification TEXT,result TEXT);CREATE TABLE meta(key TEXT,value TEXT);')
    for name,misses,score,radial,origin in [('a',1,1000,0,0),('b',0,1,20,0),('c',0,1,10,20),('d',0,1,10,10),('e',0,2,99,99)]:
        obj={'screening_revision':'dynamic-envelope-1664-v1','deficit_categories':['village']*misses,
             'baseline_score':score,'weighted_radial_dist':radial,'origin_distance':origin}
        db.execute('INSERT INTO candidates VALUES(?,0,?,\'PREDICTED\',?)',(name,name,json.dumps(obj)))
    db.commit();leaderboard.install(db)
    rows=db.execute(f'SELECT id FROM candidate_leaderboard_view ORDER BY {leaderboard.ORDER}').fetchall()
    assert [row[0] for row in rows]==['e','d','c','b','a']
    assert any('candidate_leaderboard' in str(row) for row in db.execute(f'EXPLAIN QUERY PLAN SELECT id FROM candidate_leaderboard_view ORDER BY {leaderboard.ORDER}'))


def test_legacy_fabricated_bds_shape_cannot_verify_candidate():
    record={'actual_generation_verification':{'status':'VERIFIED','source':{'kind':'actual_generation'},
            'metrics':{'paletteAgreement':'99.8%','portalRoomStatus':'INTACT'}}}
    result=server.parse_candidate_row('1',0,json.dumps(record))
    assert result['bdsVerified'] is False
    assert result['bdsAccuracy'] is None
    assert result['actualGenerationStatus']=='PENDING'


def test_web_bds_job_owns_exact_candidate_and_never_fabricates(monkeypatch,tmp_path):
    monkeypatch.setattr(server,'RUNS_DIR',tmp_path)
    manager=server.SweepManager()
    run=tmp_path/'job';run.mkdir();manager.run_dir=run;manager.status='paused'
    db=sqlite3.connect(run/'realm.sqlite')
    db.execute('CREATE TABLE candidates(id TEXT,result TEXT)')
    record={'id':'1:16:0','seed':'1','qualification':'PREDICTED',
            'biomes':{'witnesses':{'plains':{'coordinate':[16,63,0]}}}}
    raw=json.dumps(record);db.execute('INSERT INTO candidates VALUES(?,?)',(record['id'],raw));db.commit()
    class Worker:
        stdout=io.StringIO('provider unavailable\n');returncode=1
        def poll(self):return None
        def wait(self):return 1
    class Thread:
        def __init__(self,**kwargs):self.kwargs=kwargs
        def start(self):pass
    calls=[]
    monkeypatch.setattr(server.threading,'Thread',Thread)
    monkeypatch.setattr(server.subprocess,'Popen',lambda cmd,**kwargs:(calls.append(cmd),Worker())[1])
    assert not manager.verify_bds_candidate('2',record['id'])['ok']
    assert not manager.verify_bds_candidate('1','unknown')['ok']
    assert not manager.verify_bds_candidate('1',None)['ok']
    result=manager.verify_bds_candidate('1',record['id'])
    assert result['ok'] and result['status']=='bds_verifying'
    assert '--candidate' in calls[0] and 'verify-biomes' in calls[0]
    assert 'bdsVerified' not in result
    assert not manager.verify_bds_candidate('1',record['id'])['ok']
    assert db.execute('SELECT result FROM candidates').fetchone()[0]==raw
    manager._monitor_verification(*manager.monitor_thread.kwargs['args'])
    assert manager.status=='paused' and manager.error_message
    assert not list(run.glob('web-surface-points-*'))
    assert db.execute('SELECT result FROM candidates').fetchone()[0]==raw


def test_shared_raw_nether_scan_matches_independent_structure_scans():
    from seed_search.backend import Backend,ffi,lib
    from seed_search.seeds import seed_from_index
    for i in range(256):
        bounds=(-562,-562,561,561) if i%2 else (-800,-300,250,900)
        with Backend(seed_from_index(i,2026101404)) as backend:
            buffer=ffi.new('int[12288]')
            n=lib.ss_nether_raw_pair(backend._handle(),*bounds,buffer,4096)
            assert n>=0
            actual={name:sorted((int(buffer[3*j]),int(buffer[3*j+1])) for j in range(n) if bool(buffer[3*j+2])==(name=='fortress')) for name in ('fortress','bastion')}
            expected={name:sorted(backend.structures(name,bounds,False)) for name in actual}
            assert actual==expected
            assert lib.ss_nether_raw_pair(backend._handle(),*bounds,buffer,1)==(-2 if n>1 else n)


def test_website_rank_matches_four_level_tuple():
    import subprocess
    code=r'''
const fs=require('fs'),ts=require('./web-ui/node_modules/typescript'),vm=require('vm');
const source=fs.readFileSync('web-ui/src/utils/ranking.ts','utf8');
const js=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText;
const context={exports:{}};vm.runInNewContext(js,context);
const compare=context.exports.compareCandidateRank;
const make=(id,tier,score,radial,origin)=>({id,rankingTier:tier,score,weightedRadialDistance:radial,originDistance:origin,screeningRevision:'dynamic-envelope-1664-v1'});
const rows=[make('a',1,1000,0,0),make('b',0,1,20,0),make('c',0,1,10,20),make('d',0,1,10,10),make('e',0,2,99,99)];
if(rows.sort(compare).map(r=>r.id).join(',')!=='e,d,c,b,a')throw Error('Incorrect dynamic rank');
const legacy=[{id:'b',rankingTier:1,score:10,weightedRadialDistance:0},{id:'a',rankingTier:1,score:10,weightedRadialDistance:100}];
if(legacy.sort(compare)[0].id!=='a')throw Error('Historical ordering changed');
'''
    subprocess.run(['node','-e',code],check=True,capture_output=True,text=True)
