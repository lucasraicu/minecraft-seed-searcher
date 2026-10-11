"""Evidence-derived, identity-checked gate for a future finite sweep.

This protects normal launches from stale/incomplete evidence; it is not a
cryptographic attestation against somebody deliberately falsifying the files.
"""
import json
import hashlib
import re
from importlib.metadata import version
from pathlib import Path
from .storage import backend_identity, ROOT
from .review import validate_review, apply_review

CHECKS={'native_build','dependencies','tests','external_regression','deterministic_resume','end_to_end_pilot','fresh_chunkbase','candidate_quality','finite_command_validation'}


def artifact_path(value):
    p=Path(value)
    return p if p.is_absolute() else ROOT/p


def required_sources():
    return sorted([*ROOT.glob('src/seed_search/*.py'),*ROOT.glob('tests/test_*.py'),
                   ROOT/'native/build.py',ROOT/'native/bridge.c',ROOT/'native/bridge.h',
                   ROOT/'vendor/backend.json',ROOT/'pyproject.toml',ROOT/'requirements.lock',ROOT/'scripts/assemble_sweep_readiness.py'])


def derive_checks(evidence,cfg,config_hash):
    """Read measured artifacts instead of accepting a set of readiness booleans."""
    def read(key):return json.loads(artifact_path(evidence[key]).read_text())
    verification=read('verification')
    successful=lambda name: verification.get(name,{}).get('exit_code')==0 and bool(verification[name].get('command'))
    tests=verification.get('tests',{})
    test_log=artifact_path(tests.get('log','')).read_text() if artifact_path(tests.get('log','')).is_file() else ''
    passed=re.search(r'(\d+) passed',test_log)
    vendor=json.loads((ROOT/'vendor/backend.json').read_text())
    vendor_valid=all((ROOT/'vendor/cubiomes-bedrock'/name).is_file() and hashlib.sha256((ROOT/'vendor/cubiomes-bedrock'/name).read_bytes()).hexdigest()==digest for name,digest in vendor['files'].items())
    license_record=json.loads(artifact_path(verification['installed_license_evidence']).read_text())
    installed_license=artifact_path(license_record['installed_license'])
    license_valid=installed_license.is_file() and hashlib.sha256(installed_license.read_bytes()).hexdigest()==vendor['files']['LICENSE']
    versions=json.loads(artifact_path(verification['dependency_versions_evidence']).read_text())
    dependency_valid=versions.get('all_locked_versions_match') is True and bool(versions.get('packages')) and all(version(name)==p['locked']==p['installed'] for name,p in versions['packages'].items())
    regression=read('regression')
    resume=read('resume')
    from .storage import Store
    pilot=artifact_path(evidence['pilot'])
    store=Store(pilot,resume=True)
    try:
        identity=store.identity;results=store.results()
    finally:store.close()
    invocations=[json.loads(p.read_text()) for p in sorted(pilot.glob('invocation-*.json'))]
    current=identity['backend']==backend_identity() and identity['config_sha256']==config_hash and identity['config']==cfg
    complete=len(results)==identity['count'] and len(results)>=10 and len({r['seed'] for r in results})==len(results)
    measurements=bool(invocations) and sum(r['completed_this_invocation'] for r in invocations)==len(results) and all(
        r['wall_seconds']>=r['analysis_wall_seconds']>0 and r['report_wall_seconds']>=0 and r['actual_worker_pids'] and r['parent_peak_rss_mb']>0 and r['worker_peak_rss_mb']>0
        for r in invocations)
    candidates=[c for r in results for c in r['candidates']]
    reviews=read('fresh_reviews')
    for r in reviews:
        validate_review(r,cfg)
        if r.get('config_sha256')!=config_hash:raise ValueError('Fresh review configuration differs')
        if not all(artifact_path(p).is_file() for p in r['browser_evidence']):raise ValueError('Fresh browser evidence missing')
    reviewed=[apply_review(c,reviews,cfg,config_hash) for c in candidates]
    matched=[c for c in reviewed if c['chunkbase_checked']]
    exported=json.loads((pilot/'candidates.json').read_text())
    key=lambda c:(c['seed'],tuple(c['center']),c.get('landscape_type','enclosed_island'))
    exports={key(c):c for c in exported['all_centers']}
    output_current=len(exports)==len(candidates) and exported['summary']['completed_seeds']==len(results) and all(
        exports.get(key(c),{}).get('chunkbase_review')==c['chunkbase_review'] for c in matched)
    output_current=output_current and all(len(v)==len({c['seed'] for c in v}) for v in exported['lists'].values())
    packets=list(pilot.glob('shortlist/**/candidate.json'))
    output_current=output_current and len(packets)==sum(len(v) for v in exported['lists'].values()) and all(
        (p.parent/'overworld.png').is_file() and (p.parent/'nether.png').is_file() for p in packets)
    holdouts=[c for c in matched if c['chunkbase_review'].get('review_role')=='holdout_candidate_quality']
    quality=any(c['selection_status']=='chunkbase_supported_candidate' for c in holdouts)
    controls=read('fresh_geometry')
    fresh=bool(holdouts) and any(int(c['seed'])>>32 for c in matched) and any(min(c['center'])<0 for c in matched) and controls.get('source_kind')=='fresh_chunkbase_browser_UI' and controls.get('terrain_enabled') is True and len(controls.get('cases',[]))>=2 and all(artifact_path(p).is_file() for case in controls['cases'] for p in case['evidence'])
    command=read('command_validation')
    return {
        'native_build':successful('native_build') and verification.get('vendor_source_hashes_verified') is True and vendor_valid and license_valid,
        'dependencies':successful('dependencies') and dependency_valid,
        'tests':successful('tests') and tests.get('passed_count',0)>=74 and tests.get('failed_count')==0 and passed is not None and int(passed.group(1))==tests['passed_count'] and not re.search(r'\d+ failed|ERROR|FAILED',test_log),
        'external_regression':regression.get('passed') is True and regression['summary']['unique_type_correspondences']==874 and regression['summary']['known_structure_disagreements']==6 and regression['summary']['reused_starts']==0,
        'deterministic_resume':resume.get('equal') is True and resume.get('candidate_count',0)>0 and resume.get('seeds_compared',0)>=10 and resume.get('prediction_sha256')==resume.get('uninterrupted_prediction_sha256') and resume.get('current_backend_identity')==backend_identity() and resume.get('config_sha256')==config_hash and resume.get('worker_variation_test_passed') is True,
        'end_to_end_pilot':current and complete and measurements and bool(candidates) and output_current,
        'fresh_chunkbase':fresh,
        'candidate_quality':quality,
        'finite_command_validation':command.get('tiny_equivalent_exit_code')==0 and command.get('large_gate_rejection_exit_code')==2 and command.get('resume_dry_run_exit_code')==0 and command.get('sweep_unstarted') is True and command.get('maximum_count',0)>1000,
    }


def check_readiness(path,cfg,config_hash,count):
    if not path:raise ValueError('Large sweep requires --readiness pointing to verified evidence')
    p=Path(path);r=json.loads(p.read_text())
    if r.get('ready') is not True:raise ValueError('Readiness record is not ready')
    if r.get('config_sha256')!=config_hash or r.get('backend_identity')!=backend_identity():
        raise ValueError('Readiness identity is incompatible with current configuration/backend')
    if set(r.get('checks',{}))!=CHECKS or not all(v is True for v in r['checks'].values()):
        raise ValueError('Readiness checks are incomplete')
    if not 1000<count<=r.get('maximum_sweep_count',0):raise ValueError('Sweep exceeds measured readiness budget')
    artifacts=r.get('artifacts',[])
    if not artifacts:raise ValueError('Readiness requires verification artifacts')
    covered=set()
    for a in artifacts:
        f=artifact_path(a['path']).resolve();covered.add(f)
        if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest()!=a['sha256']:
            raise ValueError(f'Readiness artifact missing or changed: {f}')
    if not set(required_sources())<=covered:raise ValueError('Readiness source/test manifest is incomplete')
    evidence=r.get('evidence',{})
    needed={'verification','regression','resume','pilot','fresh_reviews','fresh_geometry','command_validation'}
    if set(evidence)!=needed:raise ValueError('Readiness evidence links are incomplete')
    linked={artifact_path(v).resolve() for k,v in evidence.items() if k!='pilot'}
    verification=json.loads(artifact_path(evidence['verification']).read_text())
    linked|={artifact_path(verification[k]['log']).resolve() for k in ('native_build','dependencies','tests')}
    linked|={artifact_path(verification[k]).resolve() for k in ('installed_license_evidence','dependency_versions_evidence')}
    vendor=json.loads((ROOT/'vendor/backend.json').read_text())
    linked|={ROOT/'vendor/cubiomes-bedrock'/name for name in vendor['files']}
    pilot=artifact_path(evidence['pilot']).resolve()
    linked|={pilot/'checkpoint.sqlite',*pilot.glob('invocation-*.json')}
    reviews=json.loads(artifact_path(evidence['fresh_reviews']).read_text())
    linked|={artifact_path(v).resolve() for review in reviews for v in review['browser_evidence']}
    geometry=json.loads(artifact_path(evidence['fresh_geometry']).read_text())
    linked|={artifact_path(v).resolve() for case in geometry['cases'] for v in case['evidence']}
    if not linked<=covered:raise ValueError('Readiness evidence is not fully hashed')
    command=json.loads(artifact_path(evidence['command_validation']).read_text())
    if r['maximum_sweep_count']!=command['maximum_count'] or r.get('sweep_command')!=command['sweep_command'] or r.get('resume_command')!=command['resume_command']:
        raise ValueError('Readiness finite budget/commands differ from verified evidence')
    actual=derive_checks(evidence,cfg,config_hash)
    if actual!=r['checks']:raise ValueError('Readiness assertions do not match measured evidence')
    return r
