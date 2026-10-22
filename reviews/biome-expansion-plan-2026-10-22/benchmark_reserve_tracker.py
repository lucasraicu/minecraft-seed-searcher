"""Synthetic selection/persistence cost; no seed generation or production writes."""
import argparse
import json
import sqlite3
import statistics
import time
import tracemalloc
from seed_search.realm.top_tracker import Top50Tracker


def run(count=10000,repeats=5):
    records=[dict(seed=str(i),anchors=[dict(seed=str(i),id=f'{i}:0:0',evaluation_center=[0,0],ranking_tier=0,
        baseline_score_observed=(i*7919)%1251,unmet_requirements=0,radial_key=i%31,origin_distance_squared=0)]) for i in range(count)]
    def order(row):
        a=row['anchors'][0];return (-a['baseline_score_observed'],a['radial_key'],a['id'])
    expected=sorted(records,key=order);results={}
    for capacity in (50,100):
        timings=[];flushes=[]
        for _ in range(repeats):
            tracker=Top50Tracker(capacity=capacity,winner_limit=50)
            start=time.perf_counter()
            for row in records:tracker.observe(row)
            timings.append(time.perf_counter()-start)
            assert [r['seed'] for r in tracker.top_records()]==[r['seed'] for r in expected[:capacity]]
            with sqlite3.connect(':memory:') as db:
                start=time.perf_counter();tracker.flush(db);flushes.append(time.perf_counter()-start)
                assert db.execute('select count(*) from top_candidates').fetchone()[0]==capacity
        tracemalloc.start();tracker=Top50Tracker(capacity=capacity,winner_limit=50)
        for row in records:tracker.observe(row)
        live,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
        results[str(capacity)]=dict(heap_median_seconds=statistics.median(timings),sqlite_flush_median_seconds=statistics.median(flushes),heap_live_python_bytes=live,heap_peak_python_bytes=peak)
    return dict(records=count,repeats=repeats,results=results,heap_time_ratio=results['100']['heap_median_seconds']/results['50']['heap_median_seconds'],limitations='Synthetic adversarial score stream, in-memory SQLite, no BDS/native seed search. Production native work can increase because the reserve cutoff is lower; no throughput promise.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);args=p.parse_args();r=run();open(args.output,'w').write(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
