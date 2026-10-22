"""Bounded read-only release checks against an already running catalog."""
import json,time,urllib.request,urllib.error,sys
from pathlib import Path
OUT=Path(__file__).resolve().parent/'http-verification'; OUT.mkdir(exist_ok=True)
SID='cd76367cbd7a679322048d534821f3017e98c9d7f57e7569568f65183074109d'
OLD='9637bc21753fa249775f0b11e84ec7a9a92d3872d7982f8e3dfd9a2be4859421'
base=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:3081'
checks=[]
def call(name,path,body=None,expect=200):
 t=time.monotonic(); req=urllib.request.Request(base+'/api/catalog/'+path,data=None if body is None else json.dumps(body).encode(),headers={'Content-Type':'application/json'})
 try:
  with urllib.request.urlopen(req,timeout=15) as r: code=r.status; d=json.load(r)
 except urllib.error.HTTPError as e: code=e.code;d=json.load(e)
 elapsed=time.monotonic()-t
 (OUT/(name+'.json')).write_text(json.dumps(d,indent=2)+'\n')
 checks.append(dict(name=name,status=code,seconds=elapsed)); assert code==expect,(name,code,str(d)[:400]);assert elapsed<10,(name,elapsed)
 return d
c=call('capabilities','capabilities'); old=call('historical-capabilities','capabilities?snapshot_id='+OLD)
for fid in ['structure.igloo_with_basement','structure.bastion_treasure']:
 assert next(x for x in c['registry_v3']['features'] if x['id']==fid)['available']
 assert not next(x for x in old['registry_v3']['features'] if x['id']==fid)['available']
s=call('snapshots','snapshots');assert SID in [x['snapshot_id'] for x in s['snapshots']]
a=call('automation-status','automation-status');assert a['state']=='paused' and a['consumed']==0 and not a['queue']['jobs'] and not a['queue']['campaigns']
def row(fid,radius):return dict(rule='required',kind='structure_count',feature=fid,at_least=1,scope=dict(kind='near_base',radius=radius))
def request(mode,rows,side=2048):return dict(request_revision='catalog-query-v3',evidence_policy='predicted_observations_v3',edition='bedrock',game_build_id='research:26.50',catalog_snapshot_id=SID,world_settings_id='default',dimension='overworld',anchor_mode=mode,border_side=side,fallback_profile='balanced_survival',rows=rows)
first=None
for mode in ['origin','recommended','world_spawn_estimated']:
 for label,fid,radius in [('igloo','structure.igloo_with_basement',1024),('treasure','structure.bastion_treasure',256)]:
  q=call(label+'-'+mode,'query',dict(request=request(mode,[row(fid,radius)]),page_size=5));assert q['ok'] and q['results'];first=first or q['results'][0]
call('mixed-8192','query',dict(request=request('recommended',[row('structure.igloo_with_basement',1024),row('structure.bastion_treasure',256)],8192),page_size=5))
req=request('origin',[row('structure.igloo_with_basement',1024)]);req['catalog_snapshot_id']=OLD
call('historical-gate','query',dict(request=req,page_size=5),400)
call('detail','detail?snapshot_id='+SID+'&world_id='+first['world_id']+'&layout_id='+first['layout_id'])
p=call('products','products')
for i,pid in enumerate(['realm.v2.qualified','preset.v2.six_pack']):
 for view in ['primary','reserve']:
  call('product-'+str(i)+'-'+view,'product-results',dict(revision='catalog-product-request-v2',snapshot_id=SID,product_id=pid,view=view,page_size=5))
(OUT/'SUMMARY.json').write_text(json.dumps(dict(ok=True,base=base,snapshot_id=SID,checks=checks),indent=2)+'\n');print(json.dumps(checks))
