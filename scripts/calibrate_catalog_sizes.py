#!/usr/bin/env python3
"""Read saved source-bound inventories to measure size-specific count saturation.

No searches, native calls, predictor changes or catalog writes. This evidence
report does not activate rankings or infer joint qualification from marginals.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import sqlite3
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from seed_search.catalog.artifacts import ArtifactStore
from seed_search.catalog.models import validate_observation,world_id,observation_id
from seed_search.catalog.registry import digest
from seed_search.catalog.geometry import bounds_for,inside,contains
from seed_search.catalog.ingestion import verify_no_symlinks

BASELINE_TIERS={
    'mansion':[1,2,3],'stronghold':[1,2,3],'monument':[1,2,3,4],
    'village':[6,7,8,9,10,11],'trial_chamber':[8,9,10,11,12,13],
    'ancient_city':[2,3,4,5,6],'desert_pyramid':[1,2,3,4],
    'outpost':[1,2,3,4],'ruined_portal':[8,9,10,11,12],
    'shipwreck':[4,5,6,7,8],'mineshaft':[10,11,12,13,14,15,16,17,18,19,20],
    'jungle_temple':[0,1,2,3],'swamp_hut':[0,1,2,3],
    'trail_ruins':[0,1,2,3],'igloo':[0,1,2],'ocean_ruin':[0,1,2],
    'buried_treasure':[0,1,2,3,4],
}


def distributions(rows):
    result={}
    for split in ('development','held_out'):
        group=[r for r in rows if r['split']==split]
        result[split]={}
        for side in (2048,4096,8192):
            values={}
            for name,tiers in BASELINE_TIERS.items():
                counts=[r['counts'][str(side)][name] for r in group if name in r['counts'][str(side)]]
                values[name]=dict(n=len(counts),histogram=dict(sorted(Counter(counts).items())),
                    at_least={str(t):sum(c>=t for c in counts) for t in tiers},
                    floor=tiers[0],cap_tier=tiers[-1],
                    capped=sum(c>=tiers[-1] for c in counts),
                    coverage_missing=len(group)-len(counts))
            result[split][str(side)]=values
    return result


def collect(root,snapshot=None):
    root=verify_no_symlinks(root)
    db=verify_no_symlinks(root/'pilot.sqlite')
    if not db.is_file() or not (root/'artifacts'/'.tmp').is_dir():raise ValueError('Existing pilot catalog required')
    artifacts=ArtifactStore(root/'artifacts')
    with sqlite3.connect(db.as_uri()+'?mode=ro',uri=True) as conn:
        snapshot=snapshot or conn.execute('SELECT snapshot_id FROM snapshot_root ORDER BY rowid DESC LIMIT 1').fetchone()[0]
        refs=conn.execute('''SELECT o.world_id,o.observation_id,a.sha256,a.relative_key,a.byte_length,a.uncompressed_length,a.codec
            FROM observation_ref o JOIN artifact_ref a ON a.sha256=o.manifest_sha256
            WHERE o.snapshot_id=? ORDER BY o.world_id''',(snapshot,)).fetchall()
        if not 1<=len(refs)<=1000:raise ValueError('Expected bounded nonempty cohort (max1000 worlds)')
        rows=[];sources=set()
        for wid,oid,*fields in refs:
            manifest=dict(zip(['sha256','relative_key','byte_length','uncompressed_length','codec'],fields))
            obs=validate_observation(artifacts.get_json(manifest))
            if world_id(obs['identity'])!=wid or observation_id(obs)!=oid:raise ValueError('Observation identity mismatch')
            sources.add(digest({k:v for k,v in obs['identity'].items() if k!='seed'}))
            counts={}
            for side in (2048,4096,8192):
                box=bounds_for([0,0],side);values={}
                for name in BASELINE_TIERS:
                    fid='structure.'+name;coverage=obs['coverage'].get(fid,{})
                    if coverage.get('status')=='complete' and contains(coverage['bounds'],box):
                        values[name]=sum(inside(x,z,box) for x,z in obs['structures'][fid])
                counts[str(side)]=values
            rows.append(dict(world_id=wid,observation_id=oid,seed=obs['identity']['seed'],
                split='held_out' if int(digest(wid),16)%5==0 else 'development',counts=counts))
    if len(sources)!=1:raise ValueError('Mixed source generations cannot be pooled')
    return dict(revision='catalog-size-calibration-evidence-v1',snapshot_id=snapshot,
        source_revision=next(iter(sources)),cohort_id=digest(rows),rows=rows,
        reference=dict(anchor=[0,0],semantics='fixed-origin calibration windows; not optimized settlement centers'),
        budgets=dict(total=1250,overworld=845,luxury=265,nether=140),
        limitations=['Legacy observations omit strongholds and Nether; no joint Realm qualification claim',
            'Igloo count is predicted starts, not the personal basement-filtered inventory',
            'Unchanged-threshold saturation is diagnostic, not an activated larger-world score',
            'Sampling provenance must be reconciled before claiming an unbiased population'],
        distributions=distributions(rows))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--snapshot');parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();output=verify_no_symlinks(args.output)
    if output.exists():raise ValueError('Refuse to overwrite calibration evidence')
    result=collect(args.root,args.snapshot)
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(worlds=len(result['rows']),cohort_id=result['cohort_id'],output=str(output))))


if __name__=='__main__':main()
