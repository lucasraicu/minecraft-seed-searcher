"""Bounded, reproducible predictor/persistence diagnostic; never a search campaign.

Uses fixed input manifests, fresh disposable checkpoints, and a separately labeled
relaxed-palette positive fixture. No BDS, remote GPU, production run or policy edit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import runpy
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
POSITIVE_SEED = '-3336796033057908633'
RUN_KEY = 20261020
STAGES = ('stronghold', 'mansion', 'jungle_temple', 'desert_pyramid',
          'monument', 'ancient_city', 'village', 'trial_chamber',
          'ruined_portal', 'shipwreck', 'mineshaft', 'nether_pair',
          'biome_palette', 'center_search', 'outpost')


def validate_budget(count, trials, threads):
    if type(count) is not int or not 1 <= count <= 16384:
        raise ValueError('count must be 1..16384')
    if type(trials) is not int or not 1 <= trials <= 5:
        raise ValueError('trials must be 1..5')
    if type(threads) is not int or not 1 <= threads <= 8:
        raise ValueError('threads must be 1..8')
    # Two matched kernel arms and one durable arm, plus a fixed warmup/diagnostics.
    inputs = count * trials * 3 + 256 + 8 + 16 + trials + 1
    if inputs > 100000:
        raise ValueError('diagnostic budget exceeds 100000 total input evaluations')
    return inputs


def summary(values):
    if not values:
        raise ValueError('Cannot summarize no measurements')
    return {'samples': values, 'median': statistics.median(values),
            'minimum': min(values), 'maximum': max(values)}


def tree_bytes(directory):
    return sum(p.stat().st_size for p in Path(directory).rglob('*') if p.is_file())


def rank(anchor):
    return (-anchor['baseline_score_observed'], anchor['radial_key'],
            anchor['origin_distance_squared'], *anchor['evaluation_center'])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True,
                        help='Fresh directory; existing paths are never overwritten')
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--count', type=int, default=8192)
    parser.add_argument('--trials', type=int, default=3)
    parser.add_argument('--threads', type=int, default=4)
    args = parser.parse_args(argv)
    budget = validate_budget(args.count, args.trials, args.threads)
    args.output.mkdir(parents=True, exist_ok=False)
    for name in ('OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'OMP_NUM_THREADS',
                 'VECLIB_MAXIMUM_THREADS'):
        os.environ[name] = '1'
    sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
    from seed_search.realm.config import dynamic_v3_blueprint_config
    from seed_search.realm.native_batch import Prototype, seeds_np, persist_pipeline
    from seed_search.realm.blueprint import evaluate_dynamic_seed
    from seed_search.realm.native_identity import native_source_fingerprint
    from seed_search.realm.runner import process_tree_resources

    started = time.monotonic()
    report = {
        'schema': 'phase2-bounded-profile-v1', 'started_at': time.time(),
        'scope': 'Pinned predictor diagnostics, not actual-world validation or public extraction',
        'controls': {'count': args.count, 'trials': args.trials,
                     'threads': args.threads, 'run_key': RUN_KEY,
                     'max_input_evaluations': budget, 'warmup_count': 256},
        'hardware': {'platform': platform.platform(), 'processor': platform.processor(),
                     'logical_cpus': os.cpu_count(), 'load_average': os.getloadavg()},
        'native_source_fingerprint': native_source_fingerprint(),
        'source_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                          for name in ('scripts/profile_phase2.py',
                                       'src/seed_search/realm/blueprint.py',
                                       'src/seed_search/realm/native_batch.py',
                                       'src/seed_search/realm/store.py',
                                       'src/seed_search/realm/config.py')},
        'kernel': [], 'durable_rejections': [], 'positive': [], 'synthetic_grid': [],
        'limitations': [
            'Shared local host; background activity is not controlled.',
            'Positive fixture has an empty required Overworld palette; not a default-blueprint survivor.',
            'No generated-world correctness/recall, GPU speed, catalog extraction or storage-size conclusion.',
            'Small stage samples are conditional diagnostics, not a production bottleneck distribution.',
            'Full-run process RSS includes adapters and retained objects; it is not per-record memory.',
        ],
    }

    def checkpoint():
        report['elapsed_seconds'] = time.monotonic() - started
        (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        if report['elapsed_seconds'] > 300:
            raise TimeoutError('Five-minute diagnostic wall budget exceeded')

    def emit(section, row):
        report[section].append(row)
        print(json.dumps({'section': section, **row}), flush=True)
        checkpoint()

    def pipeline_result(result):
        keys = ('wall_seconds', 'input_seeds_per_second', 'newly_committed',
                'native_seconds', 'record_seconds', 'preparation_wall_seconds',
                'writer_wall_seconds', 'queue_wait_seconds', 'shutdown_seconds',
                'peak_process_tree_rss_bytes', 'max_prepared_owned_estimate_bytes')
        return {key: result[key] for key in keys if key in result}

    cfg = dynamic_v3_blueprint_config()
    prototype = Prototype(args.build, cfg)
    report['build_identity'] = prototype.identity
    report['default_policy'] = cfg
    with prototype.sweep(seeds_np(0, 256, RUN_KEY), args.threads,
                         retention='survivors', refine_centers=True):
        pass
    for trial in range(args.trials):
        first = trial * args.count
        values = seeds_np(first, first + args.count, RUN_KEY)
        cohort_sha = hashlib.sha256(values.astype('<i8').tobytes()).hexdigest()
        for refinement in ((False, True) if trial % 2 == 0 else (True, False)):
            prototype.lib.nb_diag_reset()
            before = time.perf_counter()
            with prototype.sweep(values, args.threads, retention='survivors',
                                 refine_centers=refinement) as batch:
                seconds = time.perf_counter() - before
                receipt = batch.retention_receipt()
            counters = prototype.ffi.new('uint64_t[12]')
            prototype.lib.nb_diag_get(counters)
            emit('kernel', {'trial': trial, 'cohort_sha256_le_i64': cohort_sha,
                            'refinement': refinement, 'seconds': seconds,
                            'inputs_per_second': args.count / seconds,
                            'receipt': receipt,
                            'funnel_counts_native_order': list(map(int, counters))})
        run = args.output / f'rejection-pipeline-{trial}'
        result = persist_pipeline(prototype, run, args.count, run_key=RUN_KEY,
                                  start_index=first, threads=args.threads,
                                  batch_size=min(1024, args.count),
                                  retention='survivors', top_k=50)
        emit('durable_rejections', {'trial': trial, 'cohort_sha256_le_i64': cohort_sha,
                                   **pipeline_result(result), 'checkpoint_bytes': tree_bytes(run),
                                   'retained_candidates': result['status']['candidates']
                                   if 'candidates' in result['status'] else None})

    # Independent full-seed acceptance spot checks include signed boundaries.
    # A zero-positive sample is disclosed, never presented as a recall proof.
    edge_seeds = [-(1 << 63), (1 << 63) - 1, 0, 1, -1, 12345,
                  123456789, int(POSITIVE_SEED)]
    with prototype.sweep(edge_seeds, 1, retention='survivors',
                         refine_centers=False) as batch:
        native_rows = {row['seed']: row for row in batch.summary()}
    acceptance_checks = []
    for seed in edge_seeds:
        oracle = evaluate_dynamic_seed(0, seed, cfg, short_circuit=False)
        accepted = [a for a in oracle['anchors'] if a['qualification'] == 'PREDICTED']
        native = native_rows.get(str(seed), {'anchors': []})['anchors']
        assert bool(native) == bool(accepted), ('full-seed acceptance mismatch', seed)
        if accepted:
            assert native[0]['score'] == accepted[0]['baseline_score_observed']
        acceptance_checks.append({'seed': str(seed), 'accepted': bool(accepted)})
    report['independent_full_seed_acceptance'] = {
        'refinement': False, 'checks': acceptance_checks,
        'default_policy_positives': sum(row['accepted'] for row in acceptance_checks),
        'scope': 'Independent fresh Python observations vs native; fixed spot checks, not complete recall',
    }
    checkpoint()

    # Use full-retention diagnostics on eight fixed inputs. Early-outs still
    # apply; this is not the production compact-screening stage distribution.
    sample = seeds_np(0, 8, RUN_KEY)
    with prototype.sweep(sample, 1, complete=True) as batch:
        report['full_retention_stage_seconds'] = {
            name: {'entered': sum(batch.pointer.results[i].stage_seconds[k] > 0
                                  for i in range(batch.pointer.result_count)),
                   'seconds_sum': sum(float(batch.pointer.results[i].stage_seconds[k])
                                      for i in range(batch.pointer.result_count))}
            for k, name in enumerate(STAGES)}
    report['full_retention_stage_scope'] = 'Eight full-retention diagnostics; early-outs still apply; not compact production cost attribution'
    checkpoint()

    # Existing independent synthetic oracle: score/rounding/boundaries at fixed
    # 8-block centers, then compare complete coarse / hierarchical / full-fine ranks.
    helpers = runpy.run_path(str(ROOT / 'tests/test_native_refinement_parity.py'))
    p, inp, owned, inventory, palette, variants = helpers['make_case'](args.build, witness=True)
    centers = [(0, 0), (-976, -976), (976, 976), (-8, 8), (16, -16), (32, 0)]
    centers += [(x, z) for x in range(-64, 65, 16) for z in range(-32, 33, 16)]
    points = p.ffi.new('int[]', [n for center in centers for n in center])
    results = p.ffi.new('NBRefinementResult[]', len(centers))
    assert p.lib.nb_dynamic_v3_score_centers(inp, points, len(centers), results) == 0
    for center, value in zip(centers, results):
        assert helpers['native_rank'](value) == helpers['python_rank'](
            center, inventory, palette, variants, p.cfg), center
    report['independent_center_parity'] = {'centers': len(centers), 'passed': True,
                                         'scope': 'Complete synthetic inventory, not game observations'}
    ranks = {}
    for step in (16, 0, 8):
        elapsed = []
        for _ in range(args.trials):
            result = p.ffi.new('NBRefinementResult *')
            before = time.perf_counter()
            assert p.lib.nb_dynamic_v3_refine_center(inp, step, args.threads, result) == 0
            elapsed.append(time.perf_counter() - before)
        ranks[step] = helpers['native_rank'](result)
        emit('synthetic_grid', {'grid_step': step, 'seconds': summary(elapsed),
                                'rank': ranks[step], 'coarse_points': result.coarse_points,
                                'fine_points': result.fine_points})
    assert ranks[8] <= ranks[0] <= ranks[16]

    positive_cfg = dynamic_v3_blueprint_config()
    positive_cfg['biomes']['required_families'] = []
    positive_cfg['search'].update(sequence='manifest', manifest_seeds=[POSITIVE_SEED])
    positive = Prototype(args.build, positive_cfg)
    before = time.perf_counter()
    oracle = evaluate_dynamic_seed(0, POSITIVE_SEED, positive_cfg, short_circuit=False,
                                   center_grid_step=16)
    report['positive_python_coarse_oracle_seconds'] = time.perf_counter() - before
    assert oracle['anchors'], 'Known relaxed-palette fixture no longer qualifies'
    for trial in range(args.trials):
        run = args.output / f'relaxed-positive-pipeline-{trial}'
        result = persist_pipeline(positive, run, 1, threads=1, batch_size=1,
                                  retention='survivors', top_k=50)
        import sqlite3
        with sqlite3.connect(f'file:{run / "realm.sqlite"}?mode=ro', uri=True) as db:
            anchors = [json.loads(row[0]) for row in db.execute('SELECT result FROM candidates')]
            saved = json.loads(db.execute('SELECT result FROM seeds LIMIT 1').fetchone()[0])
            json_bytes = sum(db.execute(f'SELECT coalesce(sum(length(CAST(result AS BLOB))),0) FROM {table}').fetchone()[0]
                             for table in ('seeds', 'candidates'))
        assert len(anchors) == 1 and rank(anchors[0]) <= rank(oracle['anchors'][0])
        before = time.perf_counter()
        resumed = persist_pipeline(positive, run, 1, threads=1, batch_size=1,
                                   retention='survivors', top_k=50, resume=True)
        assert resumed['newly_committed'] == 0
        emit('positive', {'trial': trial, 'seed': POSITIVE_SEED,
                          'policy_exception': 'required Overworld palette empty',
                          **pipeline_result(result), 'checkpoint_bytes': tree_bytes(run),
                          'retained_candidates': len(anchors), 'rank': rank(anchors[0]),
                          'persisted_seed_stage_seconds': saved.get('stage_seconds', {}),
                          'seed_and_anchor_json_bytes': json_bytes,
                          'coarse_oracle_rank': rank(oracle['anchors'][0]),
                          'resume_seconds': time.perf_counter() - before,
                          'resume_newly_committed': resumed['newly_committed']})
    report['summary'] = {
        'kernel_refinement_on_inputs_per_second': summary([
            r['inputs_per_second'] for r in report['kernel'] if r['refinement']]),
        'kernel_refinement_off_inputs_per_second': summary([
            r['inputs_per_second'] for r in report['kernel'] if not r['refinement']]),
        'durable_rejection_inputs_per_second': summary([
            r['input_seeds_per_second'] for r in report['durable_rejections']]),
        'positive_record_wall_seconds': summary([r['wall_seconds'] for r in report['positive']]),
    }
    report['resources'] = process_tree_resources()
    report['process_cpu_seconds'] = time.process_time()
    report['complete'] = True
    checkpoint()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
