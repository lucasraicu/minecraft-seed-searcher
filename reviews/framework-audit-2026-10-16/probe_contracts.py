import hashlib,json,sqlite3,sys,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from seed_search.realm.config import dynamic_v3_blueprint_config
from seed_search.realm.blueprint import dynamic_v3_score,DYNAMIC_V3_LUXURIES
from seed_search.realm.dynamic import hub_bonus_v3,village_spread_bonus_v2,treasure_bastion_bonus_v2
from seed_search.realm.top_tracker import Top50Tracker
from seed_search.web.server import SweepManager,DEFAULT_NATIVE_BUILD
out={}
cfg=dynamic_v3_blueprint_config()
counts={k:100 for k in cfg['structures']['hard_floors']}
score,comp,_=dynamic_v3_score(counts,[m[0] for _,m in DYNAMIC_V3_LUXURIES],hub=45,scenic=1,village_spread=1,treasure_bastion=1,optional_counts={k:100 for k in ('swamp_hut','igloo','trail_ruins','ocean_ruin','buried_treasure')},nether_core=20)
out['maximum_score']={'score':score,'components':comp}
out['hub_one_portal']=hub_bonus_v3({'ruined_portal':[(0,0)]},(0,0))
out['ordinary_savanna_bonus']=dynamic_v3_score(cfg['structures']['hard_floors'],['savanna'])[0]
vs=[(900,900),(-900,900),(-900,-900)]
out['village_spread_boundary']={'default_half':village_spread_bonus_v2(vs,(0,0))[0],'v3_half':village_spread_bonus_v2(vs,(0,0),1024)[0]}
out['treasure_boundary']={'default_half':treasure_bastion_bonus_v2([(480,0)],(0,0),lambda x,z:2)[0],'v3_half':treasure_bastion_bonus_v2([(480,0)],(0,0),lambda x,z:2,512)[0]}
def anchor(seed,score=100,radial=1):
 return {'id':f'{seed}:0:0','seed':str(seed),'qualification':'PREDICTED','baseline_score':score,'baseline_score_observed':score,'radial_key':radial,'origin_distance_squared':0,'evaluation_center':[0,0],'deficit_categories':[]}
t=Top50Tracker(2)
for seed in (2,10):t.observe(anchor(seed))
out['tracker_tie_order']=[r['id'] for r in t.top_records()]
out['expected_binary_id_order']=sorted([anchor(2)['id'],anchor(10)['id']])
t=Top50Tracker(2);t.observe({'seed':'1','anchors':[anchor(1,100,999)]});t.observe({'seed':'2','anchors':[anchor(2,100,1)]})
conn=sqlite3.connect(':memory:');t.save_to_sqlite(conn)
out['nested_sqlite_scores']=conn.execute('select seed,score from top_candidates order by rank').fetchall()
t=Top50Tracker(2);r=anchor(1);t.observe(r);t.observe(r)
out['duplicate_count']=len(t)
out['new_server_default']=SweepManager().preview_sweep()['effectiveConfig']['screening_revision']
out['new_server_v3_default_misses']=SweepManager().preview_sweep(profile='dynamic2048')
out['new_server_v3_explicit_zero']=SweepManager().preview_sweep(profile='dynamic2048',max_misses=0)['ok']
out['web_native_build']=str(DEFAULT_NATIVE_BUILD)
out['web_profiles']=list(json.loads((ROOT/'web-ui/src/constants/searchProfiles.json').read_text()))
try:
 req=urllib.request.Request('http://127.0.0.1:3000/api/sweep/preview',data=json.dumps({'profile':'dynamic2048','maxMisses':0}).encode(),headers={'Content-Type':'application/json'})
 try: response=urllib.request.urlopen(req)
 except urllib.error.HTTPError as exc: response=exc
 out['running_server_v3_preview']={'http':response.status,'body':json.load(response)}
except Exception as exc:out['running_server_v3_preview']=str(exc)
for build in ('dynamic-baseline-1664','dynamic-baseline-2048'):
 meta=json.loads((ROOT/'runs'/build/'native/identity.json').read_text())
 changed=[]
 for name,h in meta['inputs'].items():
  p=ROOT/name
  if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=h:changed.append(name)
 out[build]={'flags':meta['flags'],'pgo':meta['pgo_profile_sha256'],'binary_sha':meta['extension_sha256'],'changed_sources':changed}
print(json.dumps(out,indent=2))
