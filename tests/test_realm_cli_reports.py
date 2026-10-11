import json
import yaml
import pytest
from seed_search.realm.cli import handles, main
from seed_search.realm.config import default_config
from seed_search.realm.store import RealmStore
from seed_search.realm.baseline import evaluate_seed
from seed_search.realm.reports import export,rescore
from test_realm_baseline import FakeBackend


def populated(tmp_path):
    cfg=default_config();cfg['search']['inventory_mode']='complete';s=RealmStore(tmp_path,{'config':cfg,'count':1,'start_index':0})
    s.configure_range(0,1);s.claim_range(0)
    s.complete_range(0,1,[evaluate_seed(0,1,cfg,backend_factory=FakeBackend)])
    return s,cfg


def test_legacy_argument_value_not_misrouted():
    assert not handles(['--config','config/reference-sweep.yaml','search','--count','1','--output','terrain'])
    assert handles(['search','--count','1','--output','terrain'])
    assert handles(['terrain','--run','anything'])
    assert handles(['--config=config/realm.yaml','benchmark','--output','x'])


def test_benchmark_pool_hash_pages_ids_without_decoding_observations(tmp_path,monkeypatch):
    import hashlib
    from seed_search.realm.cli import qualified_pool_digest
    s,cfg=populated(tmp_path/'run')
    try:
        expected=hashlib.sha256()
        for c in s.iter_candidates(statuses=['PREDICTED','VERIFIED']):expected.update((c['id']+'\n').encode())
        def no_observation_decode(*args,**kwargs):raise AssertionError('Benchmark hash decoded full observations')
        monkeypatch.setattr(s,'iter_candidates',no_observation_decode)
        assert qualified_pool_digest(s,batch_size=1)==expected.hexdigest()
    finally:s.close()


def test_million_benchmark_requires_one_configuration_before_creating_output(tmp_path):
    from seed_search.realm.cli import run_benchmark
    with pytest.raises(ValueError,match='one selected worker'):
        run_benchmark(default_config(),tmp_path/'million',1000000,[18,30])
    assert not (tmp_path/'million').exists()


def test_exports_include_every_anchor_and_independent_variants(tmp_path):
    s,cfg=populated(tmp_path/'run')
    try:
        ids=[r['id'] for r in s.iter_candidates()]
        s.upsert_variant(ids[0],'v1',[0,0],{'qualification':'PREDICTED_NEAR_MATCH','score':20,'geometry_score':10,'biome_fit':0,'baseline_quality':0})
        s.upsert_variant(ids[0],'v2',[0,0],{'qualification':'PREDICTED','score':90,'geometry_score':100,'biome_fit':0,'baseline_quality':0})
        result=export(s)
        assert result['exported_records']=={'baseline':2,'v1':1,'v2':1}
        assert len((s.run/'results/baseline.jsonl').read_text().splitlines())==2
        rows=[json.loads(l) for l in (s.run/'results/v2.jsonl').read_text().splitlines()]
        assert set(rows[0]['baseline']['required_structures'])==set(cfg['structures']['required'])
        score=cfg['structures']['optional_bonuses']['monument'];cfg['structures']['optional_bonuses']['monument']=score+20
        r=rescore(s,cfg)
        assert r['generation_queries']==0 and r['rescored_candidates']==2
        assert len(list(s.iter_candidates()))==2
    finally:s.close()


def test_status_compatibility_and_pending_nether(tmp_path,capsys):
    s,cfg=populated(tmp_path/'run');cid=next(s.iter_candidates())['id'];s.close()
    status=main(['status','--run',str(tmp_path/'run')])
    assert status['completed_seeds']==1
    result=main(['verify-realm','--run',str(tmp_path/'run'),'--candidate',cid])
    assert result['status']=='PARTIAL'
    output=tmp_path/'cap.json'
    result=main(['compatibility','--output',str(output)])
    assert not result['large_search_ready'] and output.is_file()


def test_automatic_pipeline_has_no_legacy_cave_invocations():
    import ast
    from pathlib import Path
    for name in ('landscapes','search'):
        tree=ast.parse(Path(f'src/seed_search/{name}.py').read_text())
        calls=[n.func.id for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)]
        assert 'deep_dark_hint' not in calls
        assert 'verify_caves' not in calls
    from seed_search.biomes import inventory,DEFAULT_WEIGHTS
    from seed_search.backend import biome_name
    ids={biome_name(i):i for i in range(256)}
    p={'version':'test','family_weights':DEFAULT_WEIGHTS,'extent_blocks2':1,'support_cells':1}
    a=inventory([ids['forest']],[[0,0]],16,(-16,-16,16,16),p,'surface_sampled')
    b=inventory([ids['forest'],ids['lush_caves']],[[0,0],[8,0]],16,(-16,-16,16,16),p,'surface_sampled')
    assert a['weighted_utility']==b['weighted_utility']
