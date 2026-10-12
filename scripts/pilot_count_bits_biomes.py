"""All active biome IDs/families: sampled support, patches and seed truncation."""
from __future__ import annotations
import argparse
from collections import defaultdict
import hashlib,json,statistics,time
from pathlib import Path
import numpy as np
from scipy.ndimage import label
from seed_search.backend import Backend,biome_catalog
from seed_search.realm.sampling import dispersed_indices
from scripts.count_pilot_api import CountBackend
from scripts.pilot_count_bits_structures import family_masks,OUT,ROOT

N=(1,)
LEVELS={0:(63,-48,0,160),-1:(33,),1:(63,)}

def grid(row,dimension,step=64):
    b=row['bounds']['nether' if dimension==-1 else 'overworld']
    xs=np.arange(-((-b[0])//step)*step,b[2]+1,step,dtype=np.int32)
    zs=np.arange(-((-b[1])//step)*step,b[3]+1,step,dtype=np.int32)
    xx,zz=np.meshgrid(xs,zs)
    points=np.concatenate([np.column_stack((xx.ravel(),np.full(xx.size,y),zz.ravel())) for y in LEVELS[dimension]]).astype(np.int32)
    return points,(len(zs),len(xs))

def patch_count(values,shape,ids,minimum_cells=1):
    # Max across horizontal layers, never sum the same 3D area repeatedly.
    size=shape[0]*shape[1]
    result=0
    for offset in range(0,len(values),size):
        array=np.isin(values[offset:offset+size].reshape(shape),list(ids))
        labeled,count=label(array)
        support=np.bincount(labeled.ravel())[1:]
        result=max(result,int(np.count_nonzero(support>=minimum_cells)))
    return result

def confusion(full,other,n):
    truth=full>=n;prediction=other>=n
    return {'tp':int(truth and prediction),'tn':int(not truth and not prediction),
            'fp':int(not truth and prediction),'fn':int(truth and not prediction)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--per-cohort',type=int,default=24)
    args=parser.parse_args()
    catalog=[r for r in biome_catalog() if r['version_active'] and r['generates']]
    masks=family_masks()
    ids_dimension={r['id']:r['dimension'] for r in catalog}
    items=[{'kind':'biome','name':r['name'],'ids':[r['id']],'dimension':r['dimension']} for r in catalog]
    items += [{'kind':'family','name':name,'ids':ids,'dimension':ids_dimension[ids[0]]} for name,ids in masks.items()]
    assert all(len({ids_dimension[i] for i in item['ids']})==1 for item in items)
    identity={'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'catalog':catalog,'items':items,'counts':N,'spacing':64,'y_levels':LEVELS,
              'scope':'48 frozen full64 layouts (24 tuning/24 holdout by default). Full64 defined sample lattice is the reference. Support counts are distinct XYZ samples; patches are 4-connected horizontal sampled components, max across layers; not actual-world exhaustive negatives or certified distinct biome areas.',
              'masked_contexts':'unsafe32/unsafe48 intentionally replace seed bits only as accuracy-negative controls, not candidate filters.'}
    (OUT/'biomes-identity.json').write_text(json.dumps(identity,indent=2)+'\n')
    observations=[];point_cases=0;count_parity=0
    for cohort in ('tuning','holdout'):
        rows=[r for r in json.loads((ROOT/f'runs/locked-stronghold-2026-10-11/{cohort}/centers.json').read_text()) if r['first_center']][:args.per_cohort]
        for index,row in enumerate(rows):
            start=time.perf_counter();record={'cohort':cohort,'seed':row['seed'],'center':row['center'],'inventories':{},'items':{}}
            contexts={'full64':Backend(row['seed']),'unsafe32':Backend(int(row['seed'])&0xffffffff),'unsafe48':Backend(int(row['seed'])&0xffffffffffff)}
            try:
                with CountBackend(row['seed']) as counted:
                    samples={};points_by_dim={};shape_by_dim={}
                    for dimension in (0,-1,1):
                        points,shape=grid(row,dimension)
                        points_by_dim[dimension]=points;shape_by_dim[dimension]=shape
                        samples[dimension]={}
                        metadata={'points':len(points),'shape':shape,'query_seconds':{},'point_disagreements':{}}
                        for arm,b in contexts.items():
                            t=time.perf_counter();samples[dimension][arm]=b.biome_points(points,dimension)
                            metadata['query_seconds'][arm]=time.perf_counter()-t
                        for arm in ('unsafe32','unsafe48'):
                            metadata['point_disagreements'][arm]=int(np.count_nonzero(samples[dimension]['full64']!=samples[dimension][arm]))
                        point_cases+=2*len(points)
                        record['inventories'][str(dimension)]=metadata
                    for item in items:
                        dimension=item['dimension'];values=samples[dimension];points=points_by_dim[dimension]
                        support={arm:int(np.count_nonzero(np.isin(v,item['ids']))) for arm,v in values.items()}
                        patches={arm:patch_count(v,shape_by_dim[dimension],item['ids']) for arm,v in values.items()}
                        robust_patches={arm:patch_count(v,shape_by_dim[dimension],item['ids'],2) for arm,v in values.items()}
                        entry={'support':support,'patches':patches,'patches_minimum_two_cells':robust_patches,'count_query':{}}
                        order=dispersed_indices(len(points));query_points=points[order]
                        for n in N:
                            t=time.perf_counter();answer,queried,capped=counted.biome_count(query_points,dimension,item['ids'],n)
                            seconds=time.perf_counter()-t
                            assert answer==(support['full64']>=n),(cohort,index,item,n)
                            assert capped==n if answer else 0<=capped<n
                            count_parity+=1
                            entry['count_query'][str(n)]={'seconds':seconds,'queried':queried,'positive':answer}
                        record['items'][item['kind']+':'+item['name']]=entry
            finally:
                for context in contexts.values():context.close()
            observations.append(record)
            if (index+1)%4==0:print(json.dumps({'biome_cohort':cohort,'complete':index+1,'last_layout_seconds':round(time.perf_counter()-start,2)}),flush=True)
            if (index+1)%8==0:(OUT/'biome-observations.json').write_text(json.dumps(observations,indent=2)+'\n')
    summaries={}
    for cohort in ('tuning','holdout'):
        rows=[r for r in observations if r['cohort']==cohort]
        inventory={}
        for dimension in (0,-1,1):
            key=str(dimension);points=sum(r['inventories'][key]['points'] for r in rows)
            seconds={arm:sum(r['inventories'][key]['query_seconds'][arm] for r in rows) for arm in ('full64','unsafe32','unsafe48')}
            inventory[key]={'points':points,'seconds':seconds,'points_per_second':{arm:points/t for arm,t in seconds.items()},
                            'point_disagreement_percent':{arm:100*sum(r['inventories'][key]['point_disagreements'][arm] for r in rows)/points for arm in ('unsafe32','unsafe48')}}
        individual={}
        for item in items:
            key=item['kind']+':'+item['name'];item_results={}
            for n in N:
                entry={'full64_support_positive':sum(r['items'][key]['support']['full64']>=n for r in rows),
                       'full64_patch_positive':sum(r['items'][key]['patches']['full64']>=n for r in rows),
                       'full64_robust_patch_positive':sum(r['items'][key]['patches_minimum_two_cells']['full64']>=n for r in rows),
                       'count_query_microseconds':1e6*statistics.mean(r['items'][key]['count_query'][str(n)]['seconds'] for r in rows),
                       'mean_queried_points':statistics.mean(r['items'][key]['count_query'][str(n)]['queried'] for r in rows),
                       'unsafe_truncation':{}}
                for arm in ('unsafe32','unsafe48'):
                    entry['unsafe_truncation'][arm]={}
                    for metric in ('support','patches'):
                        combined={k:0 for k in ('tp','tn','fp','fn')}
                        for r in rows:
                            c=confusion(r['items'][key][metric]['full64'],r['items'][key][metric][arm],n)
                            for k,v in c.items():combined[k]+=v
                        entry['unsafe_truncation'][arm][metric]=combined
                item_results[str(n)]=entry
            individual[key]=item_results
        summaries[cohort]={'inputs':len(rows),'inventory':inventory,'individual':individual,
                           'all_66_biomes_support_positive':{str(n):sum(all(r['items']['biome:'+item['name']]['support']['full64']>=n for item in catalog) for r in rows) for n in N},
                           'all_families_patch_positive':{str(n):sum(all(r['items']['family:'+name]['patches']['full64']>=n for name in masks) for r in rows) for n in N}}
    report={'cohorts':summaries,'full64_count_comparisons':count_parity,'full64_count_differences':0,'masked_point_comparisons':point_cases,
            'limits':identity['scope']+' Count-query timings are single-pass exploratory means. Both safe lower-bit strategies must retain full64 biome generation; unsafe truncation timings cannot be treated as valid speedups.'}
    (OUT/'biome-observations.json').write_text(json.dumps(observations,indent=2)+'\n')
    (OUT/'biomes-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'biomes_complete':True,'full64_count_comparisons':count_parity,'masked_point_comparisons':point_cases}),flush=True)

if __name__=='__main__':main()
