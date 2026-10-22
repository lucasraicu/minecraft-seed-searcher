"""Tiny synthetic algorithm controls, not game observations or catalog insertions."""
from pathlib import Path
import sys,json,copy,sqlite3
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
B=Path('/Users/lucasraicu/.local/share/antigravity-worker-mcp/storage-query-profile-20261022');sys.path.insert(0,str(B))
from common import DATA,SID,REG,request,structure
from seed_search.catalog.store import AutomationStore
from seed_search.catalog.query import rank_v3
store=AutomationStore(DATA);service_manifest=store.snapshot(SID);source=list(store.iter_query_summaries(dict(service_manifest,worlds=service_manifest['worlds'][:1]),8192,'recommended',lazy_features=True))[:2]
def row(index,village,igloo,known=True):
 r=dict(source[index]);r['features']=dict(source[index]['features'])
 for fid,count,complete in [('structure.village',village,known),('structure.igloo_with_basement',igloo,True)]:
  b=copy.deepcopy(r['features'][fid]);b['counts'][2]=count;b['complete'][2]=complete
  if count:b['nearest_d2']=0;b['witness']=[r['anchor'][0],None,r['anchor'][1]]
  r['features'][fid]=b
 return r
req=request(rows=[structure('structure.village'),structure('structure.igloo_with_basement')]);checks=[]
with sqlite3.connect(':memory:') as c:
 c.execute('create table f(id integer,v integer,vk integer,i integer,ik integer)')
 def compare(label,rows):
  c.execute('delete from f')
  for n,r in enumerate(rows):c.execute('insert into f values(?,?,?,?,?)',(n,r['features']['structure.village']['counts'][2],int(r['features']['structure.village']['complete'][2]),r['features']['structure.igloo_with_basement']['counts'][2],int(r['features']['structure.igloo_with_basement']['complete'][2])))
  ids=[x[0] for x in c.execute('select id from f where (v>=1 or vk=0) and (i>=1 or ik=0) order by id')]
  baseline=rank_v3(iter(rows),req,keep_keys=True,registry=REG);filtered=rank_v3((rows[i] for i in ids),req,keep_keys=True,registry=REG);assert baseline==filtered
  checks.append(dict(name=label,candidate_rows=len(ids),matched=baseline['matched_worlds'],unresolved=baseline['unresolved_worlds']));return baseline
 d=compare('ALL must share the same anchor',[row(0,1,0),row(1,0,1)]);assert d['matched_worlds']==d['unresolved_worlds']==0
 d=compare('Unknown remains pending',[row(0,0,1,False)]);assert d['matched_worlds']==0 and d['unresolved_worlds']==1
 d=compare('Known negative can be excluded',[row(0,0,1,True)]);assert d['matched_worlds']==d['unresolved_worlds']==0
 d=compare('Positive retained',[row(0,1,1)]);assert d['matched_worlds']==1
out=dict(status='PASS',scope='Synthetic conservative-prefilter correctness controls only;not saved game evidence',checks=checks);Path(__file__).with_name('PREFILTER_SEMANTICS.json').write_text(json.dumps(out,indent=2)+'\n');print(out)
