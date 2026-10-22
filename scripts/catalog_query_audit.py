#!/usr/bin/env python3
"""Offline raw-fact/index audit and exact serving measurements on a saved pilot."""
import argparse
import json
from pathlib import Path
import statistics
import sys
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))


def run(root,output):
    from seed_search.catalog.segments import SegmentedCatalog
    from seed_search.catalog.summaries import summarize
    from seed_search.catalog.index import validate_index
    from seed_search.catalog.query import search
    from seed_search.catalog.service import CatalogService
    from seed_search.catalog.evaluation import heldout_cases
    from seed_search.catalog.registry import SIDES
    from seed_search.catalog.ingestion import atomic_json
    start=time.monotonic();rows=[];by_world={};checked=0
    with SegmentedCatalog(root) as store:
        info=store.info();sid=info['snapshot_id']
        for segment in store.iter_segments(sid):
            if segment['index'] is not None:validate_index(segment['index'],layouts=segment['layouts'],trusted=False)
            for row in segment['layouts']:
                rows.append(row);by_world.setdefault(row['world_id'],{})[row['layout_id']]=row
        for wid,saved in by_world.items():
            raw=store.observation(sid,wid)
            fresh={r['layout_id']:r for r in summarize(raw)}
            if any(fresh.get(lid)!=row for lid,row in saved.items()):raise AssertionError('Saved summary differs from rederived raw coordinates')
            checked+=len(saved)
        if checked!=info['layouts']:raise AssertionError('Incomplete raw-fact audit')
    verified_seconds=time.monotonic()-start
    service=CatalogService(root,query_seconds=30);measurements=[];last_result=None
    for side in SIDES:
        for mode in ('origin','recommended'):
            for scenario in ('general','required','preferred'):
                req=dict(heldout_cases()['cases'][0]['template'],catalog_snapshot_id=sid,
                    game_build_id=info['header']['game_build_id'],world_settings_id=info['header']['world_settings_id'],
                    border_side=side,anchor_mode=mode)
                if scenario=='required':req['rows']=[dict(rule='required',kind='structure_count',feature='structure.village',at_least=3,scope=dict(kind='near_base',radius=512))]
                if scenario=='preferred':req['rows']=[dict(rule='preferred',kind='biome_witness',any_of=['biome.badlands','biome.mangrove_swamp'],importance=5,scope=dict(kind='inside_border'))]
                expected=search(rows,req,snapshot_id=sid,limit=20)
                before=time.monotonic();actual=service.query(dict(request=req,page_size=20));elapsed=time.monotonic()-before
                key=lambda results:[(r['world_id'],r['layout_id'],r['score']) for r in results]
                if key(expected)!=key(actual['results']):raise AssertionError('Serving results differ from exhaustive summaries')
                measurements.append(dict(side=side,mode=mode,scenario=scenario,seconds=elapsed,**actual['stats']))
                last_result=actual
                atomic_json(output/'query-progress.json',dict(snapshot_id=sid,completed=len(measurements),measurements=measurements))
    detail_seconds=None
    if last_result and last_result['results']:
        row=last_result['results'][-1];before=time.monotonic()
        detail=service.detail(sid,row['world_id'],row['layout_id']);detail_seconds=time.monotonic()-before
        if detail['identity']['seed']!=row['seed']:raise AssertionError('Detail seed identity mismatch')
    values=sorted(r['seconds'] for r in measurements)
    report=dict(schema='catalog-pilot-query-audit-v1',snapshot_id=sid,worlds=info['worlds'],layouts=info['layouts'],
        raw_coordinate_rederivation_layouts=checked,index_semantic_parity=True,exhaustive_top20_parity=True,
        offline_verification_seconds=verified_seconds,query_count=len(values),p50_seconds=statistics.median(values),
        p95_seconds=values[min(len(values)-1,int(.95*len(values)))],max_seconds=max(values),
        detail_seconds=detail_seconds,measurements=measurements,wall_seconds=time.monotonic()-start,
        note='Fixed18 developer requests, not representative player demand or production capacity; OS cache may be warm.')
    atomic_json(output/'query-audit.json',report);print(json.dumps(report,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False);run(args.root,args.output)
