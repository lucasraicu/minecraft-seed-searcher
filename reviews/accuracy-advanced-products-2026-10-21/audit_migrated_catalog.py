"""Independent NumPy raw-coordinate and full-sort audit; no extraction or writes to catalogs."""
import argparse
from fractions import Fraction
import json
from pathlib import Path
import sqlite3
import sys
import time
import numpy as np

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from seed_search.catalog.store import AutomationStore
from seed_search.catalog.registry import FEATURES_V2,digest


def ordered(rank):
    return tuple(Fraction(v['numerator'],v['denominator']) if isinstance(v,dict) and 'numerator'in v
                 else Fraction(v['decimal']) if isinstance(v,dict) else v for v in rank)


def audit(source,destination,output):
    started=time.monotonic();old=AutomationStore(source);new=AutomationStore(destination)
    previous=old.snapshot();current=new.snapshot();assert len(previous['worlds'])==len(current['worlds'])==222
    old_by={r['world_id']:r for r in previous['worlds']};assert set(old_by)=={r['world_id']for r in current['worlds']}
    db=sqlite3.connect((destination/'harvest.sqlite').as_uri()+'?mode=ro',uri=True)
    receipts={r[0]:json.loads(r[1])for r in db.execute('SELECT world_id,evaluations FROM automation_receipts')};db.close()
    db=sqlite3.connect((source/'harvest.sqlite').as_uri()+'?mode=ro',uri=True)
    old_receipts={r[0]:json.loads(r[1])for r in db.execute('SELECT world_id,evaluations FROM automation_receipts')};db.close()
    contract=json.loads((ROOT/'docs/catalog/v2/products.json').read_text())
    definitions={p['id']:p for p in [contract['realm'],*contract['realm_sizes'],*contract['presets'],*contract['records']]}
    families=json.loads((ROOT/'docs/catalog/v2/biome_families.json').read_text())
    numeric_checks=grid_rows=product_checks=0;qualified={p:[]for p in definitions};changed=[]
    for entry in current['worlds']:
        wid=entry['world_id'];before=old.artifacts.get_json(old_by[wid]['artifact']);after=new.artifacts.get_json(entry['artifact'])
        a=before['observation'];b=after['observation']
        assert {k:v for k,v in a.items()if k!='anchors'}=={k:v for k,v in b.items()if k!='anchors'}
        assert [r for r in a['anchors']if r['mode']!='world_spawn_estimated']==[r for r in b['anchors']if r['mode']!='world_spawn_estimated']
        anchors=[r for r in b['anchors']if r['mode']=='world_spawn_estimated'];assert len(anchors)==1
        center=anchors[0]['coordinate'];nether=[n//8 for n in center]
        old_center=next(r['coordinate']for r in a['anchors']if r['mode']=='world_spawn_estimated')
        if old_center!=center:changed.append(dict(seed=b['identity']['seed'],before=old_center,after=center))
        grid={(tuple(r['anchor']),r['border_side']):r for r in before['summaries']if 'recommended'in r['anchor_modes']}
        planes={dim:np.asarray(b['biomes'][dim],dtype=np.int64).reshape(-1,4)for dim in ('overworld','nether')}
        groups={}
        for f in FEATURES_V2:
            if f['kind']=='structure_count':groups[f['id']]=np.asarray(b['structures'].get(f['id'],[]),dtype=np.int64).reshape(-1,2)
            else:
                raw=[int(k)for k,v in b['biome_names'].items()if v in f['canonical_members']]
                plane=planes[f['dimension']];height=63 if f['dimension']=='overworld'else 64
                groups[f['id']]=plane[(plane[:,1]==height)&np.isin(plane[:,3],raw)][:,[0,2]]
        for row in after['summaries']:
            if 'recommended'in row['anchor_modes']:
                saved=grid[(tuple(row['anchor']),row['border_side'])]
                assert {k:v for k,v in saved.items()if k not in ('source_observation_id','layout_id')}=={k:v for k,v in row.items()if k not in ('source_observation_id','layout_id')};grid_rows+=1
            if 'world_spawn_estimated'not in row['anchor_modes']:continue
            assert row['anchor']==center and row['nether_anchor']==nether
            for f in FEATURES_V2:
                c=center if f['dimension']=='overworld'else nether;half=row['border_side']//2 if f['dimension']=='overworld'else 512
                pts=groups[f['id']];inside=(pts[:,0]>=c[0]-half)&(pts[:,0]<c[0]+half)&(pts[:,1]>=c[1]-half)&(pts[:,1]<c[1]+half)
                ds=((pts[inside]-np.asarray(c))**2).sum(axis=1);radii=(256,512,1024)if f['dimension']=='overworld'else(64,128,256)
                counts=[int((ds<=radius*radius).sum())for radius in radii]+[len(ds)]
                if f['kind']!='structure_count':counts=[int(n>0)for n in counts]
                actual=row['features'][f['id']]
                assert actual['counts']==counts,(wid,row['border_side'],f['id'])
                assert actual['nearest_d2']==(int(ds.min())if len(ds)else None)
                numeric_checks+=1
        def complete(feature,c,r):
            cov=b['coverage'].get(feature,{});bounds=cov.get('bounds',[])
            return cov.get('status')=='complete' and len(bounds)==4 and bounds[0]<=c[0]-r and bounds[1]<=c[1]-r and bounds[2]>=c[0]+r+1 and bounds[3]>=c[1]+r+1
        def distances(feature,c,r):
            pts=groups[feature];ds=((pts-np.asarray(c))**2).sum(axis=1)
            return sorted(int(n)for n in ds if n<=r*r)
        def biome_distance(family,dim,c,r):
            plane=planes[dim];ids=[int(k)for k,v in b['biome_names'].items()if v in families['features'][family]]
            pts=plane[(plane[:,1]==(63 if dim=='overworld'else 64))&np.isin(plane[:,3],ids)][:,[0,2]]
            ds=((pts-np.asarray(c))**2).sum(axis=1);valid=ds[ds<=r*r]
            return int(valid.min())if len(valid)else None
        for evaluation in receipts[wid]:
            p=definitions[evaluation['product_id']];dim=p.get('dimension','overworld');c=center if dim=='overworld'else nether;r=p.get('radius')
            assert evaluation['observation_id']==entry['observation_id']
            if p['id'].startswith('realm.'):
                # Realm uses its saved independent settlement center; only source binding changes.
                before_eval=next(e for e in old_receipts[wid]if e['product_id']==p['id'])
                assert {k:v for k,v in before_eval.items()if k!='observation_id'}=={k:v for k,v in evaluation.items()if k!='observation_id'}
            elif p.get('kind')in('density','proximity'):
                ds=distances(p['feature'],c,r);known=complete(p['feature'],c,r)
                status='pending'if p['kind']=='density'and not known else'match'if ds else'no_match'if known else'pending'
                assert evaluation['status']==status
                if status=='match':assert evaluation['rank']==([-len(ds)]if p['kind']=='density'else[ds[0]])
                product_checks+=1
            elif 'structures'in p:
                expected=[];status='match'
                for feature,n in p['structures'].items():
                    ds=distances(feature,c,r)
                    if len(ds)<n:
                        status='no_match'if complete(feature,c,r)else'pending';break
                    expected+=ds[:n]
                if status=='match':
                    for family in p['biomes']:
                        d=biome_distance(family,dim,c,r)
                        if d is None:status='pending';break
                        expected.append(d)
                assert evaluation['status']==status
                if status=='match':assert evaluation['rank']==[max(expected),sum(expected)]
                product_checks+=1
            if evaluation['status']=='match':
                qualified[p['id']].append(evaluation)
                if r is not None:
                    for witness in evaluation['witnesses']:
                        x,y,z=witness['coordinate'];assert witness['observation_id']==entry['observation_id']
                        assert witness['distance_squared']==(x-c[0])**2+(z-c[1])**2<=r*r
    for pid,p in definitions.items():
        expected=sorted(qualified[pid],key=lambda e:(ordered(e['rank']),e['world_id']))[:p['capacity']]
        actual=[m['member']for m in current['memberships']if m['objective_id']==pid]
        assert actual==expected,pid
    # Every copied old immutable snapshot remains readable at its original ID.
    for record in old.snapshots():assert new.snapshot(record['snapshot_id'])==old.snapshot(record['snapshot_id'])
    result=dict(worlds=222,changed_world_anchors=len(changed),changes=changed,feature_scope_numeric_checks=numeric_checks,
        unchanged_recommended_rows=grid_rows,independent_preset_density_proximity_checks=product_checks,
        full_sort_product_boards=len(definitions),source_snapshot=digest(previous),snapshot_id=digest(current),
        seconds=time.monotonic()-started,cluster_scope='Existing evaluator regression suite plus raw witness-distance and full-sort membership checks; no physical-instance claim')
    output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='changes'},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--destination',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args();audit(a.source,a.destination,a.output)
