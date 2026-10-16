from pathlib import Path
import copy,json,sys,tempfile
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).parent
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
from seed_search.realm.config import dynamic_v2_blueprint_config
from seed_search.realm.native_batch import Prototype,NAMES
from seed_search.realm.reports import _candidate_rescore
from seed_search.realm.store import RealmStore,canonical
from seed_search.web import server
from scripts.shard_campaign import partition_campaign
from scripts.merge_runs import merge_runs
from seed_search.realm.leaderboard import order_for
cfg=dynamic_v2_blueprint_config();p=Prototype('/tmp/followup-233fad7-native',cfg)
r={}
for name,arr in [('float64',np.array([1.0])),('int32',np.array([1,2],dtype=np.int32))]:
    try:
        with p.sweep(arr,retention='survivors'):r[name]='ACCEPTED'
    except (TypeError,ValueError) as exc:r[name]=str(exc)
for name,target in [('village',10),('ruined_portal',8),('trial_chamber',9)]:
    custom=copy.deepcopy(cfg);custom['structures']['minimum_counts'][name]=target
    q=Prototype('/tmp/followup-233fad7-native',custom)
    with q.sweep([456],fixtures=[(0,0,NAMES.index(name))]) as b:
        a=b.records()[0]['anchors'][0]
        r['custom_'+name]={'score':a['baseline_score'],'penalty':a['deficit_penalty'],'saved_target':a['configured_targets'][name]}
with p.sweep([456],fixtures=[(0,0,-1)]) as b:a=b.records()[0]['anchors'][0]
(OUT/'positive-anchor.json').write_text(json.dumps(a,indent=2)+'\n')
r['variant_evidence']=a.get('bastion_variants')
x,z=a['evaluation_center'];sx=64*round(x/64);sz=64*round(z/64)
for row in a['biomes']['sampling']['samples']:
    if row['coordinate']==[sx,63,sz]:row['biome']='plains'
    if row['coordinate']==[sx+64,63,sz]:row['biome']='river'
a['scenic_bonus']=0;a['scenic_witness']=None;a['river_witness']=None
low=_candidate_rescore(copy.deepcopy(a),{},'audit')['baseline_score']
a['scenic_bonus']=20
high=_candidate_rescore(copy.deepcopy(a),{},'audit')['baseline_score']
r['same_evidence_scenic_rescore']={'flag0':low,'flag20':high,'difference':high-low}
class Captured(Exception):pass
def capture(c):r['web_configuration']={'revision':c['screening_revision'],'budget':c['search']['max_misses'],'terrain':c['terrain']['variants']};raise Captured()
with patch.object(server,'validate_config',capture):
    try:server.SweepManager.__new__(server.SweepManager).start_sweep(count=1,threads=1)
    except Captured:pass
s=partition_campaign()[0]
r['shard_defaults']={'config':s.config,'revision':__import__('yaml').safe_load(Path(s.config).read_text())['screening_revision'],'budget':s.max_misses,'count':s.count,'command':s.cli_command}
# A long-lived reader must see a committed writer's progress.
with tempfile.TemporaryDirectory() as d:
    with RealmStore(d,{'config':cfg,'retention':{'mode':'survivors','max_misses':3}}) as writer:
        writer.configure_range(0,1,1)
        with RealmStore(d,resume=True) as reader:
            before=reader.status()['completed_seeds']
            writer.claim_range('writer')
            receipt={'version':'native-retention-receipt-v1','inputs':1,'retained_inputs':0,'retained_anchors':0,'discovered_anchors':0,'input_decisions_sha256':'e'*64}
            writer.complete_prepared(writer.prepare_retained_range(0,1,[],receipt))
            r['cached_reader']={'before':before,'after':reader.status()['completed_seeds'],'database':json.loads(reader.db.execute("SELECT value FROM meta WHERE key='completed_seeds'").fetchone()[0])}
# Explicitly synthetic ranking records, with equal supporting geometry.
with tempfile.TemporaryDirectory() as d:
    sources=[]
    for i,(score,defs) in enumerate([(100,['village']),(50,[])]):
        path=Path(d)/str(i);sources.append(path)
        with RealmStore(path,{'config':cfg}) as st:
            st.configure_range(i,i+1,1)
            row=copy.deepcopy(a);row.update(id=f'{i}:0:0',seed=str(i),evaluation_center=[0,0],baseline_score=score,baseline_score_observed=score,deficit_categories=defs,radial_key=0,origin_distance_squared=0)
            with st.db:
                st.db.execute('INSERT INTO candidates VALUES (?,?,?,?,?)',(row['id'],str(i),str(i),'PREDICTED',canonical(row)))
                st.db.execute("UPDATE ranges SET status='complete'")
    merged=merge_runs(sources,Path(d)/'merged')
    import sqlite3
    with sqlite3.connect(merged['destination']) as db:
        expected=db.execute('SELECT seed,smart_score FROM candidate_leaderboard_view ORDER BY '+order_for(db)).fetchall()
    r['merge_rank']={'reported':merged['top_candidates'],'canonical':expected}
(OUT/'probe-results.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r,indent=2))
