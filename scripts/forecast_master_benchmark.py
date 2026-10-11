"""Small matched baseline trials, then save a forecast before the sole million run."""
import argparse
import json
from pathlib import Path
import statistics
import time

from seed_search.realm.cli import load,run_benchmark,make_identity
from seed_search.realm.resources import disk_policy,disk_status


def main(output):
    root=Path(output);root.mkdir(parents=True,exist_ok=True)
    cfg=load('config/realm.yaml');rows=[]
    for trial,workers in enumerate(((18,30,36),(36,30,18),(30,18,36))):
        result=run_benchmark(cfg,root/f'trial-{trial}',1000,list(workers))
        rows.extend(dict(r,trial=trial) for r in result['rows'])
    assert len({json.loads((root/f'trial-{t}'/'benchmark.json').read_text())['rows'][0]['qualified_pool_sha256'] for t in range(3)})==1
    medians={str(n):statistics.median(r['wall_seconds'] for r in rows if r['workers']==n) for n in (18,30,36)}
    winner=int(min(medians,key=medians.get))
    # Keep the historical setting when the small-cohort gain is within 5%.
    selected=30 if medians['30']<=medians[str(winner)]*1.05 else winner
    result=run_benchmark(cfg,root/'forecast-pilot',10000,[selected])
    pilot=result['rows'][0];hours=1000000/pilot['seeds_per_second']/3600
    million=root.parent/'million';million.mkdir(exist_ok=True)
    forecast={'recorded_at_unix':time.time(),'requested_full64_inputs':1000000,
              'selected_workers':selected,'native_threads_per_worker':1,
              'matched_trials':rows,'median_seconds_1000':medians,
              'selection_policy':'Fastest median; retain 30 if within 5%; isolated baseline only',
              'forecast_pilot':pilot,'point_estimate_hours':hours,
              'working_range_hours':[hours*.9,hours*1.5],
              'historical_hours':[1.355436710864747,2.700411002554589],
              'predicted_database_bytes':pilot['storage_bytes']/10000*1000000,
              'initial_disk_preflight':disk_status(million,disk_policy(cfg['search']),remaining_seeds=1000000),
              'identity':make_identity(cfg,1000000,0),
              'scope':'One million permutation inputs at run_key 0; startup, required Overworld+both final Nether, checkpoint included; no terrain/BDS; prediction only. Small pilot is not sustained large-database evidence.'}
    (root.parent/'million-forecast.json').write_text(json.dumps(forecast,indent=2)+'\n')
    print(json.dumps({k:forecast[k] for k in ('selected_workers','point_estimate_hours','working_range_hours','predicted_database_bytes')},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    main(parser.parse_args().output)
