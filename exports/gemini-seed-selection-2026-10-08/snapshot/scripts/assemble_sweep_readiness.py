"""Assemble the finite-sweep gate only from independently saved measured evidence."""
import argparse
import hashlib
import json
from pathlib import Path
from datetime import datetime,timezone
from seed_search.config import load_config
from seed_search.storage import ROOT,backend_identity
from seed_search.readiness import derive_checks,required_sources,check_readiness


def assemble(config,evidence_path,output,maximum_count):
    cfg,h=load_config(config)
    evidence=json.loads(Path(evidence_path).read_text())
    checks=derive_checks(evidence,cfg,h)
    missing=[k for k,v in checks.items() if not v]
    if missing:raise ValueError('Not ready: '+', '.join(missing))
    command=json.loads(Path(evidence['command_validation']).read_text())
    if maximum_count!=command['maximum_count']:raise ValueError('Finite command budget differs')
    pilot=Path(evidence['pilot'])
    verification=json.loads(Path(evidence['verification']).read_text())
    reviews=json.loads(Path(evidence['fresh_reviews']).read_text())
    geometry=json.loads(Path(evidence['fresh_geometry']).read_text())
    paths=set(required_sources())|{Path(config),Path(evidence_path),Path(__file__),ROOT/'requirements.lock'}
    paths|={Path(v) for k,v in evidence.items() if k!='pilot'}
    paths|={Path(verification[k]['log']) for k in ('native_build','dependencies','tests')}
    paths|={pilot/'checkpoint.sqlite',pilot/'run.json',pilot/'summary.json',pilot/'candidates.json',pilot/'candidates.csv',*pilot.glob('invocation-*.json'),*pilot.rglob('shortlist/*/candidate.json')}
    paths|={Path(p) for r in reviews for p in r['browser_evidence']}
    paths|={Path(p) for r in geometry['cases'] for p in r['evidence']}
    vendor=json.loads((ROOT/'vendor/backend.json').read_text())
    paths|={ROOT/'vendor/cubiomes-bedrock'/name for name in vendor['files']}
    paths|={ROOT/'fixtures/bedrock-26.52/chunkbase-accuracy-audit.json',ROOT/'fixtures/bedrock-26.52/local-regression-baseline.json'}
    paths|=set(pilot.rglob('shortlist/**/*.png'))|set(pilot.rglob('shortlist/**/candidate.json'))
    paths|={ROOT/'SWEEP_READINESS.md',ROOT/'runs/sweep-readiness/STRUCTURE_HANDLING.md',ROOT/'runs/sweep-readiness/structure-diagnostics.json',ROOT/'runs/sweep-readiness/exact-land-optimization.json'}
    paths|={ROOT/'runs/sweep-readiness/dependency-versions.json',ROOT/'runs/sweep-readiness/installed-license.json',ROOT/'runs/sweep-readiness/doctor.json',ROOT/'runs/sweep-readiness/fresh-coordinate-comparison.json',ROOT/'fixtures/bedrock-26.52/fresh-coordinate-points.json'}
    paths|={ROOT/'runs/sweep-readiness/memory-budget.json',ROOT/'runs/sweep-readiness/pilot-measurements.json',ROOT/'scripts/write_sweep_readiness_report.py',ROOT/'scripts/compare_fresh_coordinates.py',ROOT/'runs/sweep-readiness/review-refresh-measurement.json',ROOT/'runs/sweep-readiness/review-refresh.log'}
    paths|={ROOT/'runs/sweep-readiness/final-checks.json',ROOT/'runs/sweep-readiness/gate-tests.log'}
    paths|={ROOT/command[k] for k in ('tiny_equivalent_evidence','large_gate_rejection_evidence','resume_evidence')}
    if command.get('large_sweep_dry_run_evidence'):paths.add(ROOT/command['large_sweep_dry_run_evidence'])
    if pilot.parent.name=='landscape-expansion':
        work=pilot.parent
        paths|={ROOT/'LANDSCAPE_EXPANSION.md',ROOT/'CHUNKBASE_WORKFLOW.md',ROOT/'README.md',
                ROOT/'scripts/verify_expanded_pilot.py',ROOT/'scripts/write_expanded_readiness_report.py',
                ROOT/'scripts/benchmark_exact_cache.py',ROOT/'scripts/audit_repeated_compute.py',
                ROOT/'scripts/verify_report_reuse.py'}
        paths|={work/name for name in ('pilot-measurements.json','cache-ab.json','baseline-12853964.json',
                                      'fresh-prediction-comparison.json','scoring-order-diagnostic.json',
                                      'report-reuse-proof.json','doctor.json','FINAL_VERIFICATION_BUDGET.md')}
    if pilot.parent.name=='filter-optimization':
        work=pilot.parent
        paths|={ROOT/'FILTER_OPTIMIZATION.md',ROOT/'README.md',ROOT/'CHUNKBASE_WORKFLOW.md',
                ROOT/'scripts/verify_expanded_pilot.py',ROOT/'scripts/benchmark_filter_shortcuts.py',
                ROOT/'scripts/verify_report_reuse.py',ROOT/'scripts/write_filter_readiness.py',
                work/'shortcuts-ab.json',work/'shortcuts-ab.log',work/'pilot-measurements.json',
                work/'optimization-parity.json',work/'report-reuse-proof.json',work/'doctor.json',work/'fresh-marker-comparison.json',work/'worker-ab.json',
                work/'memory-budget.json',work/'final-gate-checks.json',ROOT/'GOAL.md',ROOT/'PROGRESS.md',work/'workers8-uninterrupted/checkpoint.sqlite',work/'workers8-uninterrupted/invocation-000.json',
                work/'repeat-20-workers12/checkpoint.sqlite',work/'repeat-20-workers12/invocation-000.json',
                work/'config/review-all.yaml',work/'WORK.md',pilot/'stronghold-deferred.json',
                pilot/'stronghold-deferred-seeds.txt'}
    artifacts=[{'path':str(p.resolve()),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(paths) if p.is_file()]
    r={'schema':1,'ready':True,'recorded_at':datetime.now(timezone.utc).isoformat(),'config_path':str(Path(config).resolve()),'config_sha256':h,'backend_identity':backend_identity(),'maximum_sweep_count':maximum_count,'checks':checks,'evidence':{k:str(Path(v).resolve()) for k,v in evidence.items()},'artifacts':artifacts,'sweep_command':command['sweep_command'],'resume_command':command['resume_command'],'sweep_unstarted':True}
    Path(output).write_text(json.dumps(r,indent=2)+'\n')
    check_readiness(output,cfg,h,maximum_count)
    return r


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',required=True);p.add_argument('--evidence',required=True);p.add_argument('--output',required=True);p.add_argument('--maximum-count',type=int,required=True)
    a=p.parse_args();r=assemble(a.config,a.evidence,a.output,a.maximum_count)
    print(json.dumps({'ready':r['ready'],'checks':r['checks'],'artifact_count':len(r['artifacts']),'maximum_sweep_count':r['maximum_sweep_count']},indent=2))
