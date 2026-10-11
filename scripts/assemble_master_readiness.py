"""Seal implementation evidence; never authorize an actual production sweep."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import time

from seed_search.realm.cli import load, make_identity
from seed_search.realm.capabilities import report

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def assemble(output):
    root = Path(output).resolve()
    read = lambda name: json.loads((root / name).read_text())
    audit = read('million-audit.json')
    launch = read('benchmark-launch.json')
    assert audit['status'] == 'PASS' and audit['distinct_full64_inputs'] == 1000000
    assert not audit['actual_generation_verified'] and not audit['production_sweep_started']
    assert audit['mandatory_nether_violations'] == 0
    assert audit['all_candidate_nether_bounds_checked'] == sum(audit['candidate_counts'].values())
    assert all(v == 0 for v in audit['all_stored_final_nether_start_violations'].values())
    cfg = load(str(ROOT / 'config/realm.yaml'))
    assert make_identity(cfg, 1000000, 0) == launch['identity']
    assert read('native-parity-threads4.json')['status'] == 'PASS'
    threads = read('all-native-thread-counts.json')
    assert threads['status'] == 'PASS' and threads['native_thread_counts'] == list(range(1, 37))
    assert read('full-capacity-thread-trials.json')['arrays_equal']
    assert read('terrain-trials.json')['semantic_outputs_equal']
    assert read('terrain-capacity-trials.json')['semantic_outputs_equal']
    schedules = read('schedules/report.json')
    assert schedules['arrays_equal'] and schedules['installed_native_unchanged']
    assert schedules['native_threads'] == 18
    attempted = {'static', 'dynamic64', 'guided64'}
    assert set(schedules['attempted_schedules']) == attempted
    measured = set(schedules['measured_schedules'])
    unavailable = {row['schedule'] for row in schedules['unavailable_schedules']}
    assert 'static' in measured and not measured & unavailable and measured | unavailable == attempted
    assert all(row['status'] == 'UNSUPPORTED' and row['reason'] for row in schedules['unavailable_schedules'])
    assert {row['schedule'] for row in schedules['rows']} == measured
    assert len(schedules['rows']) == 9 * len(measured)
    assert read('isa/trials.json')['public_and_raw_arrays_equal']
    assert read('safety/report.json')['status'] == 'PASS'
    trace = read('stronghold-trace/report.json')
    assert len(trace['seeds']) == 7 and all(r['trace_matches_installed_village_starts'] for r in trace['seeds'])
    assert not trace['actual_game_trace_available']
    joined = read('terrain-attribution/joined-evidence-report.json')
    assert joined['columns'] == 256 and joined['all_model_columns_joined']
    assert not joined['current_natural_ground_policy_verified']
    borders = read('border-comparison/report.json')
    assert borders['production_config_unchanged'] and not borders['production_profile_changed']
    assert len(borders['trials']) == 9 and borders['nether_side_blocks'] == 1024
    test_log = (root / 'post-million-tests.log').read_text()
    matches = re.findall(r'(\d+) passed in ([\d.]+)s', test_log)
    assert matches and int(matches[-1][0]) >= 623 and 'failed' not in test_log.lower()
    source_paths = {ROOT / name for name in launch['source_hashes']}
    source_paths.update(p for folder in ('src', 'scripts', 'tests', 'native') for p in (ROOT / folder).rglob('*')
                        if p.is_file() and p.suffix in ('.py', '.c', '.h', '.js', '.sh', '.json'))
    source_paths.update(ROOT / name for name in ('MASTER_IMPLEMENTATION_PLAN.md', 'MASTER_IMPLEMENTATION_RESULTS.md', 'MASTER_SWEEP_READINESS.md', 'SWEEP_READINESS.md', 'STRONGHOLD_INVESTIGATION.md', 'requirements.lock', 'pyproject.toml', 'config/realm.yaml'))
    source_hashes = {str(p.relative_to(ROOT)): sha256(p) for p in sorted(source_paths)}
    artifacts = ('benchmark-launch.json', 'million-forecast.json', 'million-audit.json', 'million/benchmark.json',
                 'reference-tests.log', 'reference-hashes.json', 'pre-change-source.tar.gz', 'reference_native.so',
                 'native-parity-threads4.json', 'native-timing.json', 'all-native-thread-counts.json',
                 'full-capacity-thread-trials.json', 'terrain-trials.json', 'terrain-capacity-trials.json',
                 'schedules/report.json',
                 'isa/trials.json', 'isa/cpu.json', 'safety/report.json', 'funnel-final/report.json',
                 'terrain-attribution/report.json', 'terrain-attribution/columns.csv', 'terrain-attribution/joined-columns.csv',
                 'terrain-attribution/joined-evidence-report.json', 'stronghold-trace/report.json',
                 'border-comparison/report.json', 'million-parent-sample.txt', 'post-million-tests.log')
    artifact_hashes = {name: sha256(root / name) for name in artifacts}
    artifact_hashes.update({f"stronghold-trace/{row['seed']}.jsonl": sha256(root / 'stronghold-trace' / f"{row['seed']}.jsonl") for row in trace['seeds']})
    actual_source = ROOT / joined['source']
    assert sha256(actual_source) == joined['source_sha256']
    capability = report(cfg)
    assert capability['large_search_ready'] is False
    (root / 'final-compatibility.json').write_text(json.dumps(capability, indent=2) + '\n')
    artifact_hashes['final-compatibility.json'] = sha256(root / 'final-compatibility.json')
    result = {'schema': 1, 'recorded_at_unix': time.time(),
              'implementation_delivery_verified': True, 'large_search_ready': False,
              'production_sweep_started': False, 'production_launch_authorized': False,
              'one_million_benchmark': {'inputs': 1000000, 'coverage_audit': 'PASS',
                                       'workers': audit['benchmark']['workers'],
                                       'native_threads_per_worker': 1,
                                       'wall_seconds': audit['benchmark']['wall_seconds'],
                                       'seeds_per_second': audit['benchmark']['seeds_per_second'],
                                       'actual_generation_verified': False},
              'final_suite': {'passed': int(matches[-1][0]), 'seconds': float(matches[-1][1])},
              'baseline_identity': make_identity(cfg, 1000000, 0),
              'source_sha256': source_hashes, 'artifact_sha256': artifact_hashes,
              'retained_actual_source': {'path': joined['source'], 'sha256': joined['source_sha256'],
                                         'current_natural_ground_policy_verified': False},
              'selected_solo_profiles': {'baseline': {'processes': 30, 'native_threads': 1},
                                         'terrain': {'processes': 1, 'native_threads': 18}},
              'optional_decisions': {'priority': 'implemented opt-in; rotation retained',
                                     'openmp_schedule': schedules['decision'],
                                     'avx2': 'strict probe passed; shipping deferred',
                                     'avx512': 'unsupported OS vector state',
                                     'raw_front_door': 'promotion gate failed; ranking adapter retained',
                                     'metal': 'deferred', 'coast_c_port': 'deferred',
                                     'hard_approximate_exits': 'unproved; not installed'},
              'open_production_gates': ['exact-build required-structure acquisition and Stronghold recall',
                                        'complete actual natural V1/V2 positive/negative reference formations and halos',
                                        'natural support/liquid/ice/structure provenance and held-out calibration',
                                        'sustained intended-workload and concurrent BDS resource/backlog measurements'],
              'scope': 'Current implementation and bounded prediction verification evidence. This seal is advisory and is not a launch capability, a game-accuracy certificate or an exhaustive seed search.'}
    (root / 'readiness.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('implementation_delivery_verified', 'large_search_ready', 'one_million_benchmark', 'final_suite', 'open_production_gates')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    assemble(parser.parse_args().output)
