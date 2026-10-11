"""Read-only coverage and required-Nether audit after the sole million run."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import time

from seed_search.realm.cli import load,make_identity
from seed_search.realm.runner import _seed


def audit(output):
    root=Path(output).resolve();launch=json.loads((root/'benchmark-launch.json').read_text())
    forecast=json.loads((root/'million-forecast.json').read_text())
    benchmark=json.loads((root/'million/benchmark.json').read_text())
    assert len(benchmark['rows'])==1 and benchmark['distinct_full64_inputs']==1000000
    row=benchmark['rows'][0];assert row['completed_seeds']==row['count']==1000000
    cfg=load('config/realm.yaml');assert make_identity(cfg,1000000,0)==launch['identity']==forecast['identity']
    for relative,expected in launch['identity']['backend']['sha256'].items():
        assert hashlib.sha256(Path(relative).read_bytes()).hexdigest()==expected,relative
    documentation_changes={}
    for relative,expected in launch['source_hashes'].items():
        observed=hashlib.sha256(Path(relative).read_bytes()).hexdigest()
        if observed!=expected:
            # This document is not read by the benchmark. Its post-launch edits
            # link the current checklist and distinguish planning from execution.
            assert relative=='MASTER_IMPLEMENTATION_PLAN.md',relative
            documentation_changes[relative]={'launch_sha256':expected,'current_sha256':observed,
                'reason':'Post-launch execution/checklist documentation; not a computational input'}
    run=root/'million'/f"workers-{row['workers']}";begin=time.perf_counter()
    db=sqlite3.connect((run/'realm.sqlite').as_uri()+'?mode=ro',uri=True)
    try:
        assert db.execute('PRAGMA quick_check').fetchall()==[('ok',)]
        get=lambda key:json.loads(db.execute('SELECT value FROM meta WHERE key=?',(key,)).fetchone()[0])
        assert get('completed_seeds')==1000000 and get('range')==[0,1000000]
        assert get('worker_statistics')['error'] is None and not get('worker_statistics')['interrupted']
        at=0;ranges=0
        for first,end,status in db.execute('SELECT start,end,status FROM ranges ORDER BY start'):
            assert int(first)==at and status=='complete' and int(end)>at
            at=int(end);ranges+=1
        assert at==1000000
        digest=hashlib.sha256();completed=0
        for index,seed in db.execute('SELECT idx,seed FROM seeds ORDER BY idx'):
            assert int(index)==completed and seed==str(_seed(completed,cfg['search']))
            digest.update(f'{index}:{seed}\n'.encode());completed+=1
        assert completed==1000000
        distinct=db.execute('SELECT count(DISTINCT seed) FROM seeds').fetchone()[0]
        assert distinct==1000000
        assert not db.execute("SELECT 1 FROM candidates WHERE qualification='VERIFIED' LIMIT 1").fetchone()
        # Decode each payload once in a bounded streaming scan. Repeated SQL
        # json_extract calls otherwise reread large overflow payloads many times.
        # Bounded integer discovery coordinates make /8.0 and +/-512 exact binary
        # arithmetic; the separate Fraction helper replay below checks that fact.
        bad=0;start_violations={'fortress':0,'bastion':0};checked=0;stored_starts=0
        print(json.dumps({'audit_stage':'all_candidate_nether_bounds','status':'running'}),flush=True)
        for cid,idx,seed,qualification,payload in db.execute('SELECT id,idx,seed,qualification,result FROM candidates'):
            candidate=json.loads(payload);center=candidate['stronghold']
            assert candidate['id']==cid==f'{seed}:{center[0]}:{center[1]}'
            assert candidate['index']==int(idx) and candidate['seed']==seed
            assert seed==str(_seed(int(idx),cfg['search']))
            assert all(isinstance(v,int) and not isinstance(v,bool) and -2500<=v<2500 for v in center)
            bounds=[center[0]/8.0-512,center[1]/8.0-512,center[0]/8.0+512,center[1]/8.0+512]
            assert candidate['bounds']['final_nether']==bounds
            assert candidate['final_nether_status']=='UNVERIFIED'
            prediction=candidate['final_nether_prediction']
            assert prediction['actual_generation_verified'] is False
            assert prediction['required']==['fortress','bastion'] and prediction['bounds']==bounds
            found=[]
            for name in ('fortress','bastion'):
                observation=candidate['required_nether_structures'][name]
                assert observation['bounds']==bounds
                points=observation['predicted_viable'];found.append(bool(points))
                assert isinstance(points,list)
                for p in points:
                    assert len(p)==2 and all(isinstance(v,int) and not isinstance(v,bool) for v in p)
                    assert bounds[0]<=p[0]<bounds[2] and bounds[1]<=p[1]<bounds[3],(cid,name,p)
                    stored_starts+=1
            assert prediction['status']==('PREDICTED' if all(found) else 'PENDING')
            if qualification=='PREDICTED':assert all(found)
            checked+=1
            if checked%100000==0:print(json.dumps({'audit_stage':'all_candidate_nether_bounds','checked_candidates':checked}),flush=True)
        # Sample stored starts independently of their suitability score. Membership
        # is checked against the exact public helpers, without new generation.
        from seed_search.realm.bounds import nether_square,contains,json_bounds
        sampled=0
        for payload, in db.execute("SELECT result FROM candidates WHERE qualification='PREDICTED' ORDER BY id LIMIT 1024"):
            candidate=json.loads(payload);bounds=nether_square(candidate['stronghold'])
            assert candidate['bounds']['final_nether']==json_bounds(bounds)
            for name in ('fortress','bastion'):
                observation=candidate['required_nether_structures'][name]
                assert observation['bounds']==json_bounds(bounds)
                assert all(contains(p,bounds) for p in observation['predicted_viable'])
            sampled+=1
        counts=get('counts');candidate_counts=dict(db.execute('SELECT qualification,count(*) FROM candidates GROUP BY qualification'))
        assert sum(candidate_counts.values())==counts['stronghold_anchors']
        report={'status':'PASS','audit_seconds':time.perf_counter()-begin,'coverage_range':[0,1000000],
                'distinct_full64_inputs':distinct,'complete_nonoverlapping_ranges':ranges,
                'seed_sequence_sha256':digest.hexdigest(),'quick_check':'ok','mandatory_nether_violations':bad,
                'all_stored_final_nether_start_violations':start_violations,
                'all_candidate_nether_bounds_checked':checked,'stored_final_nether_starts_checked':stored_starts,
                'launch_source_hashes_preserved':len(launch['source_hashes'])-len(documentation_changes),
                'launch_documentation_changes':documentation_changes,
                'exact_border_sampled_candidates':sampled,'candidate_counts':candidate_counts,'counts':counts,
                'benchmark':row,'forecast_point_hours':forecast['point_estimate_hours'],
                'measured_hours':row['wall_seconds']/3600,
                'speed_ratio_vs_forecast':row['seeds_per_second']/forecast['forecast_pilot']['seeds_per_second'],
                'within_working_range':forecast['working_range_hours'][0]<=row['wall_seconds']/3600<=forecast['working_range_hours'][1],
                'historical_hours':forecast['historical_hours'],'actual_generation_verified':False,
                'production_sweep_started':False,'scope':'Baseline prediction only; terrain/BDS not included; pending evidence retained'}
    finally:db.close()
    (root/'million-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('benchmark','counts')},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    audit(parser.parse_args().output)
