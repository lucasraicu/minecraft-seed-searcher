"""Independent read-only source/history/rank oracle for the final successor."""
from concurrent.futures import ProcessPoolExecutor
import copy
import hashlib
import json
import multiprocessing
from pathlib import Path
import sqlite3
import sys
import time

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from seed_search.catalog.store import AutomationStore
from seed_search.catalog.registry import digest
from seed_search.catalog import automation

SOURCE=Path('/Users/lucasraicu/.local/share/antigravity-worker-mcp/biome-expansion-approved-20261022/catalog-corrected')
TARGET=Path('/Users/lucasraicu/.local/share/antigravity-worker-mcp/treasure-activation-approved-20261022/catalog')
FIDS=('structure.igloo_with_basement','structure.bastion_treasure')

def check_world(args):
    old_entry,new_entry,reg,deadline=args
    if time.monotonic()>deadline:raise TimeoutError('Read-only audit allocation')
    old_store=AutomationStore(SOURCE);new_store=AutomationStore(TARGET)
    a=old_store.artifacts.get_json(old_entry['artifact']);b=new_store.artifacts.get_json(new_entry['artifact'])
    assert a['observation']==b['observation']and a['extension_artifact']==b['extension_artifact']
    obs=a['observation'];assert digest(obs)==old_entry['observation_id']==new_entry['observation_id']
    assert old_entry['identity']==new_entry['identity']and len(a['summaries'])==len(b['summaries'])
    mapping={};offers={};rows=0;feature_checks=0
    for old,row in zip(a['summaries'],b['summaries']):
        assert {k:v for k,v in old.items()if k not in('registry_revision','layout_id')}=={k:v for k,v in row.items()if k not in('registry_revision','layout_id')}
        assert row['registry_revision']==digest(reg)
        assert row['layout_id']==digest(['catalog-summary-v3',row['source_observation_id'],row['source_extension_id'],row['sampling_profile_revision'],digest(reg),row['anchor'],row['anchor_modes'],row['border_side']])
        mapping[old['layout_id']]=row['layout_id'];rows+=1
        for fid in FIDS:
            igloo=fid==FIDS[0];kind='igloo_basement'if igloo else'bastion_variant';parent='structure.igloo'if igloo else'structure.bastion'
            inv=obs['realm']['inventory'][kind];parents=set(map(tuple,obs['structures'][parent]));points=set()
            for p in inv['points']:
                if(igloo or p[2]==2)and tuple(p[:2])in parents:points.add(tuple(p[:2]))
            center=row['anchor']if igloo else row['nether_anchor'];half=row['border_side']//2 if igloo else 512
            cx,cz=center;lo=(cx-half,cz-half);hi=(cx+half,cz+half);radii=(256,512,1024)if igloo else(64,128,256)
            hits=sorted(((x-cx)**2+(z-cz)**2,x,z)for x,z in points if lo[0]<=x<hi[0]and lo[1]<=z<hi[1])
            counts=[len([h for h in hits if h[0]<=r*r])for r in radii]+[len(hits)]
            completeness=[]
            for radius in(*radii,None):
                query=[*lo,*hi]if radius is None else[max(lo[0],cx-radius),max(lo[1],cz-radius),min(hi[0],cx+radius+1),min(hi[1],cz+radius+1)]
                covered=[]
                for coverage in(inv,obs['coverage'][parent]):
                    bounds=coverage.get('bounds',[])
                    covered.append(coverage.get('status')=='complete'and len(bounds)==4 and bounds[0]<=query[0]and bounds[1]<=query[1]and bounds[2]>=query[2]and bounds[3]>=query[3])
                completeness.append(all(covered))
            expected=dict(dimension='overworld'if igloo else'nether',counts=counts,complete=completeness,nearest_d2=hits[0][0]if hits else None,witness=[hits[0][1],None,hits[0][2]]if hits else None)
            assert row['features'][fid]==expected,(obs['identity']['seed'],row['anchor'],fid,row['features'][fid],expected)
            feature_checks+=1
            if not hits or(not igloo and row['border_side']!=2048):continue
            modes=[m for m in('origin','recommended')if m in row['anchor_modes']]
            if'world_spawn_estimated'in row['anchor_modes']and any(x['mode']=='world_spawn_estimated'and x['coordinate']==row['anchor']for x in obs['anchors']):modes.append('spawn')
            d,x,z=hits[0];wid=row['world_id'];ax,az=row['anchor'];rank=[d,wid,ax,az,x,0,z]
            for mode in modes:
                oid='v3.near:'+fid+':'+((str(row['border_side'])+':')if igloo else'')+mode
                member=dict(world_id=wid,layout_id=row['layout_id'],anchor=row['anchor'],source_observation_id=row['source_observation_id'],witness=[x,None,z],feature_id=fid,rank=rank)
                off=dict(objective_id=oid,world_id=wid,rank=rank,member=member)
                if oid not in offers or rank<offers[oid]['rank']:offers[oid]=off
    for side in(2048,4096,8192):assert new_store._projection(new_entry,side)==[r for r in b['summaries']if r['border_side']==side]
    return dict(world_id=new_entry['world_id'],mapping=mapping,rows=rows,feature_checks=feature_checks,offers=list(offers.values()))

def main():
    started=time.monotonic();old=AutomationStore(SOURCE).snapshot();new=AutomationStore(TARGET).snapshot();a={e['world_id']:e for e in old['worlds']};b={e['world_id']:e for e in new['worlds']};assert set(a)==set(b)and len(a)==222
    members=copy.deepcopy(old['memberships']);by_world={wid:[]for wid in a}
    for m in members:by_world[m['world_id']].append(m)
    offers={};row_count=feature_checks=0
    with ProcessPoolExecutor(max_workers=4,mp_context=multiprocessing.get_context('spawn'))as pool:
        for result in pool.map(check_world,((a[w],b[w],new['registry'],started+180)for w in a)):
            row_count+=result['rows'];feature_checks+=result['feature_checks']
            for m in by_world[result['world_id']]:
                lid=m['member'].get('layout_id')
                if lid in result['mapping']:m['member']['layout_id']=result['mapping'][lid]
            for off in result['offers']:offers.setdefault(off['objective_id'],[]).append(off)
    existing={(m['objective_id'],m['world_id']):m for m in members};actual={(m['objective_id'],m['world_id']):m for m in new['memberships']};assert len(actual)==len(new['memberships'])
    for k,v in existing.items():assert actual[k]==v,k
    extra=[]
    for oid,candidates in offers.items():
        assert len({x['world_id']for x in candidates})==len(candidates)
        chosen=sorted(candidates,key=lambda x:x['rank'])[:40];extra.extend(chosen)
        assert sorted([m for m in new['memberships']if m['objective_id']==oid],key=lambda x:x['rank'])==chosen,oid
    assert len(offers)==12 and set(actual)==set(existing)|{(m['objective_id'],m['world_id'])for m in extra}
    assert old['reserve_policy']==new['reserve_policy']and old['product_status']==new['product_status']and old['population_worlds']==new['population_worlds']
    assert automation.configuration(SOURCE)['options']==automation.configuration(TARGET)['options']
    original=sqlite3.connect((SOURCE/'harvest.sqlite').as_uri()+'?mode=ro',uri=True);successor=sqlite3.connect((TARGET/'harvest.sqlite').as_uri()+'?mode=ro',uri=True)
    for wid,oid,evaluations in original.execute('SELECT world_id,observation_id,evaluations FROM automation_receipts'):
        assert successor.execute('SELECT observation_id,evaluations FROM automation_receipts WHERE world_id=?',(wid,)).fetchone()==(oid,evaluations)
    original.close();successor.close()
    checked_files=0
    for relative in('artifacts','accuracy','evidence','product-previews','automation/objects','automation/snapshots','automation/generations'):
        src=SOURCE/relative
        if not src.exists():continue
        for path in src.rglob('*'):
            if not path.is_file():continue
            target=TARGET/path.relative_to(SOURCE);assert target.is_file()and hashlib.sha256(path.read_bytes()).digest()==hashlib.sha256(target.read_bytes()).digest(),str(path);checked_files+=1
    result=dict(status='PASS',source_snapshot=digest(old),successor_snapshot=digest(new),worlds=len(a),summary_rows=row_count,variant_feature_oracles=feature_checks,old_memberships_preserved=len(existing),new_variant_lists=len(offers),new_variant_memberships=len(extra),immutable_history_files_verified=checked_files,seconds=time.monotonic()-started)
    out=Path(__file__).parent/'FINAL_SUCCESSOR_AUDIT.json';out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
