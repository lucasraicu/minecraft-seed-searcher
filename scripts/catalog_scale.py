#!/usr/bin/env python3
"""Explicitly fabricated 1,000-world storage/index parity probe; no seed extraction."""
import argparse
import copy
import json
from pathlib import Path
import resource
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))


def run(output):
    from seed_search.catalog.models import identity,empty_observation,world_id,observation_id
    from seed_search.catalog.codec import layout_id
    from seed_search.catalog.registry import STRUCTURES,ENVELOPE,SIDES
    from seed_search.catalog.summaries import summarize
    from seed_search.catalog.segments import SegmentedCatalog
    from seed_search.catalog.service import CatalogService
    from seed_search.catalog.query import search
    from seed_search.catalog.evaluation import heldout_cases
    from seed_search.catalog.ingestion import atomic_json
    output.mkdir(parents=True,exist_ok=False)
    start=time.monotonic()
    template=empty_observation(identity(0,model_id='FABRICATED_SCALE',native_sha256='a'*64,source_sha256='b'*64))
    for feature in STRUCTURES:
        template['structures'][feature['id']]=[[0,0],[256,128],[512,512]]
        template['coverage'][feature['id']]={'status':'complete','bounds':list(ENVELOPE),'method_id':'predictor_viable_starts_v1'}
    base=[row for row in summarize(template) if row['anchor'] in ([0,0],[256,0])]
    rows=[];parent=None
    with SegmentedCatalog(output/'catalog',leaf_entries=4,fanout=4) as store:
        for first in range(0,1000,25):
            batch=[];summaries=[]
            for seed in range(first,first+25):
                obs=copy.deepcopy(template);obs['identity']['seed']=str(seed)
                wid=world_id(obs['identity']);oid=observation_id(obs);batch.append(obs)
                for saved in base:
                    row=copy.deepcopy(saved)
                    row.update(seed=str(seed),world_id=wid,observation_id=oid,layout_id=layout_id(oid,row['anchor'],row['border_side']))
                    summaries.append(row)
            rows.extend(summaries);parent=store.publish(batch,summaries,parent=parent)
        audit=store.audit(parent);info=store.info(parent)
    published=time.monotonic()-start
    service=CatalogService(output/'catalog',query_seconds=120)
    measurements=[]
    for side in SIDES:
        for mode in ('origin','recommended'):
            request=dict(heldout_cases()['cases'][0]['template'],catalog_snapshot_id=parent,
                game_build_id=info['header']['game_build_id'],world_settings_id='default',border_side=side,anchor_mode=mode,
                rows=[dict(rule='required',kind='structure_count',feature='structure.village',at_least=2,scope=dict(kind='near_base',radius=512))])
            expected=search(rows,request,snapshot_id=parent,limit=50)
            for repeat in range(2):
                before=time.monotonic();result=service.query(dict(request=request,page_size=50))
                actual=[(r['world_id'],r['layout_id'],r['score']) for r in result['results']]
                oracle=[(r['world_id'],r['layout_id'],r['score']) for r in expected]
                if actual!=oracle:raise AssertionError('Indexed Top50 differs from exhaustive synthetic oracle')
                measurements.append(dict(side=side,mode=mode,repeat=repeat,seconds=time.monotonic()-before,**result['stats']))
                atomic_json(output/'progress.json',dict(completed_queries=len(measurements),measurements=measurements))
    report=dict(schema='catalog-fabricated-scale-v1',fabricated=True,worlds=1000,layouts=len(rows),
        audit=audit,publish_and_audit_seconds=published,measurements=measurements,
        process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        wall_seconds=time.monotonic()-start,note='Fabricated identical spatial facts under distinct world identities; not natural diversity or player-demand evidence.')
    atomic_json(output/'report.json',report)
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args().output)
