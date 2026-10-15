"""Isolated Sol audit setup and explicitly gated native experiments.

Run from the repository root. Only `prepare` is suitable while benchmarks are
paused. Build/train/bench require --allow-heavy after the user releases the Mac.
"""
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'reviews/split-audit-2026-10-15/sol'
WORK = Path('/tmp/minecraft-sol-audit-20261015')
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
OPENMP = ROOT / 'runs/master-implementation-2026-10-10/openmp/install'
ARMS = ('control', 'lazy', 'no-surface-init', 'lazy-no-surface-init', 'dark-gate')


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + '\n')


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f'Expected one source anchor: {old[:90]!r}')
    return text.replace(old, new, 1)


def lazy_source(text):
    text = replace_once(text,
        'w->ctx->seed=seed;applySeed(&w->ctx->overworld,DIM_OVERWORLD,seed);\n'
        '    applySeed(&w->ctx->nether,DIM_NETHER,seed);',
        'w->ctx->seed=seed;')
    text = replace_once(text,
        '    if(!w->p->retention) {\n        code=nb_dynamic_discovery(w,r,ow);',
        '    if(!w->p->retention) {\n'
        '        applySeed(&w->ctx->overworld,DIM_OVERWORLD,seed);\n'
        '        code=nb_dynamic_discovery(w,r,ow);')
    anchor = '    /* One inexpensive macro Mansion preflight before all other structure inventories. */'
    text = replace_once(text, anchor,
        '    if(w->p->retention)applySeed(&w->ctx->overworld,DIM_OVERWORLD,seed);\n' + anchor)
    return replace_once(text, '    code=nb_nether(w,nw,&nether_macro);',
        '    applySeed(&w->ctx->nether,DIM_NETHER,seed);\n'
        '    code=nb_nether(w,nw,&nether_macro);')


def no_surface_source(text):
    start = text.index('    case Mansion:', text.index('int isViableStructurePos('))
    end = text.index('    case Ruined_Portal:', start)
    block = text[start:end]
    block = replace_once(block,
        '                SurfaceNoise sn;\n'
        '                initSurfaceNoise(&sn, DIM_OVERWORLD, g->seed);\n',
        '                /* This MC_1_18+ path does not read SurfaceNoise. */\n')
    block = replace_once(block,
        'mapApproxHeight(&height, &biome_id, g, &sn, x >> 2, z >> 2, 1, 1);',
        'mapApproxHeight(&height, &biome_id, g, NULL, x >> 2, z >> 2, 1, 1);')
    return text[:start] + block + text[end:]


def dark_gate_source(text):
    helper = '''/* Necessary Y=63 witness only; positive seeds retain full inventories. */
static int nb_audit_dark_possible(NBWorker *w,const int *b) {
    if(w->fixture)return 1;
    StructureConfig cfg;if(!getStructureConfig(Mansion,MC_26_50,&cfg))return -1;
    int size=cfg.regionSize*16,n=0;
    for(int rx=floordiv(b[0],size);rx<=floordiv(b[2],size);rx++)
      for(int rz=floordiv(b[1],size);rz<=floordiv(b[3],size);rz++) {
        Pos p;
        if(getStructurePos(Mansion,MC_26_50,w->ctx->seed,rx,rz,&p)&&
           inside(p,b[0],b[1],b[2],b[3])&&
           nb_point(w,p.x,63,p.z)==w->p->dark_id&&++n>=w->p->goals[0])return 1;
      }
    return 0;
}
'''
    text = replace_once(text, 'static int nb_eval_dynamic(', helper + 'static int nb_eval_dynamic(')
    return replace_once(text, '    code=nb_pair(w,0,feasible,&macro[0]);if(code)goto done;',
        '    possible=nb_audit_dark_possible(w,feasible);\n'
        '    if(possible<0){code=possible;goto done;}if(!possible)goto done;\n'
        '    code=nb_pair(w,0,feasible,&macro[0]);if(code)goto done;')


def prepare():
    from seed_search.realm.config import dynamic_blueprint_config
    OUT.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    production = json.loads((ROOT / 'runs/dynamic-baseline-1664/native/identity.json').read_text())
    mismatches = [name for name, digest in production['inputs'].items()
                  if not (ROOT / name).is_file()
                  or hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest]
    if mismatches:
        raise ValueError(f'Production source mismatch: {mismatches}')
    extension_hash = hashlib.sha256(Path(production['extension']).read_bytes()).hexdigest()
    if extension_hash != production['extension_sha256']:
        raise ValueError('Production extension hash differs from its identity')
    runtime_hash = hashlib.sha256(Path(production['runtime']).read_bytes()).hexdigest()
    if runtime_hash != production['runtime_sha256']:
        raise ValueError('OpenMP runtime hash differs from its identity')
    for arm in ARMS:
        target = WORK / arm
        if target.exists():
            raise ValueError(f'Refusing to overwrite prepared arm: {target}')
        shutil.copytree(ROOT / 'native', target / 'native')
        shutil.copytree(ROOT / 'vendor/cubiomes-bedrock', target / 'vendor/cubiomes-bedrock')
        (target / 'scripts').mkdir()
        shutil.copy2(ROOT / 'scripts/build_blueprint_batch.py', target / 'scripts/build_blueprint_batch.py')
        edits = {}
        dynamic = 'native/blueprint_dynamic.inc'
        if arm in ('lazy', 'lazy-no-surface-init', 'dark-gate'):
            edits[dynamic] = lazy_source((target / dynamic).read_text())
        if arm == 'dark-gate':
            edits[dynamic] = dark_gate_source(edits[dynamic])
        if arm in ('no-surface-init', 'lazy-no-surface-init', 'dark-gate'):
            name = 'vendor/cubiomes-bedrock/finders.c'
            edits[name] = no_surface_source((target / name).read_text())
        patch = ''
        for name, text in edits.items():
            original = (ROOT / name).read_text()
            (target / name).write_text(text)
            patch += ''.join(difflib.unified_diff(original.splitlines(True), text.splitlines(True),
                                                fromfile='a/' + name, tofile='b/' + name))
        if patch:
            path = OUT / 'proposals' / (arm + '.patch')
            path.parent.mkdir(exist_ok=True)
            path.write_text(patch)
    policy = dynamic_blueprint_config()
    config_hash = hashlib.sha256(json.dumps(policy, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    manifest = {
        'status': 'prepared; heavy work awaiting explicit user release',
        'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'policy': policy, 'policy_sha256': config_hash,
        'production_build': production,
        'production_extension_sha256_checked': extension_hash,
        'production_runtime_sha256_checked': runtime_hash,
        'host': subprocess.check_output(['sysctl', 'hw.physicalcpu', 'hw.logicalcpu', 'hw.memsize',
                                         'machdep.cpu.brand_string'], text=True).splitlines(),
        'platform': sys.platform, 'python': sys.version,
        'cpu_note': '18 physical / 36 logical on this host; no affinity or SMT assumptions',
        'work_directory': str(WORK),
        'arms': list(ARMS),
        'proposed_workloads': {
            'training': {'run_key': 2026101402, 'start_index': 0, 'count': 10000,
                         'fixtures': [[0, 0, -1]], 'threads': 4},
            'profile': {'run_key': 2026101401, 'start_index': 50000000, 'count': 100000},
            'screen': {'run_key': 2026101401, 'start_index': 51000000, 'count': 100000, 'trials': 3},
            'confirm': {'run_key': 2026101401, 'start_index': 52000000, 'count': 500000, 'trials': 5},
            'retention': 'survivors', 'max_misses': 2,
            'default_batch_size': 16384, 'default_threads': 34,
        },
        'natural_late_stage_inputs': 'to be collected by diagnostics; no natural survivor claimed',
        'synthetic_provenance': 'native NBFixture interface; not actual seed-world discoveries',
        'exclusions': ['end-to-end runs', 'BDS', 'production source/binary replacement'],
    }
    write_json(OUT / 'manifest.json', manifest)
    print('Prepared isolated sources, candidate patches, and manifest. No compilation or timing ran.')


def build(arm, chunk, phase):
    from scripts import build_blueprint_batch as builder
    source = WORK / arm
    builder.ROOT = source
    output = source / f'chunk-{chunk}' / phase
    kwargs = dict(openmp_prefix=OPENMP, work_chunk=chunk, cpu_native=True, lto=True)
    if phase == 'training':
        kwargs['pgo_generate'] = True
    else:
        kwargs['pgo_use'] = source / f'chunk-{chunk}' / 'trained.profdata'
    result = builder.build(output, **kwargs)
    write_json(OUT / 'builds' / f'{arm}-{chunk}-{phase}.json', result)
    print(result['extension'])


def build_diagnostic():
    from scripts import build_blueprint_batch as builder
    builder.ROOT = WORK / 'diagnostic'
    result = builder.build(WORK / 'diagnostic' / 'native-build', openmp_prefix=OPENMP,
                           work_chunk=16, cpu_native=True, lto=True)
    write_json(OUT / 'builds' / 'diagnostic.json', result)
    print(result['extension'])


def train(arm, chunk):
    base = WORK / arm / f'chunk-{chunk}'
    os.environ['LLVM_PROFILE_FILE'] = str(base / 'train-%p.profraw')
    from seed_search.realm.native_batch import Prototype
    from seed_search.realm.config import dynamic_blueprint_config
    from seed_search.seeds import seed_from_index
    p = Prototype(base / 'training', dynamic_blueprint_config())
    with p.sweep([seed_from_index(i, 2026101402) for i in range(10000)], 4, retention='survivors'):
        pass
    with p.sweep([1], fixtures=[(0, 0, -1)], retention='survivors'):
        pass
    # Profile files flush at process exit. Merge is deliberately a separate command.


def merge(arm, chunk):
    base = WORK / arm / f'chunk-{chunk}'
    tool = subprocess.check_output(['xcrun', '--find', 'llvm-profdata'], text=True).strip()
    raw = sorted(base.glob('train-*.profraw'))
    if not raw:
        raise ValueError('No training profile files; run train in a separate process first')
    profile = base / 'trained.profdata'
    subprocess.run([tool, 'merge', '-output', str(profile), *map(str, raw)], check=True)
    meta = json.loads((base / 'training/identity.json').read_text())
    meta['profile_sha256'] = hashlib.sha256(profile.read_bytes()).hexdigest()
    write_json(profile.with_suffix('.json'), meta)


def benchmark(args):
    from seed_search.realm.native_batch import Prototype
    from seed_search.realm.config import dynamic_blueprint_config
    from seed_search.seeds import seed_from_index
    rows = []
    prototypes = {arm: Prototype(WORK / arm / f'chunk-{args.chunk}' / 'optimized',
                                 dynamic_blueprint_config()) for arm in args.arms}
    for trial in range(args.trials):
        start = args.start + trial * args.count
        seeds = [seed_from_index(i, 2026101401) for i in range(start, start + args.count)]
        order = list(args.arms)
        if trial % 2:
            order.reverse()
        digests = []
        for arm in order:
            p = prototypes[arm]
            before_cpu = time.process_time()
            native = 0.
            batch_times = []
            digest = hashlib.sha256()
            content = hashlib.sha256()
            survivors = 0
            for offset in range(0, len(seeds), args.batch):
                with p.sweep(seeds[offset:offset + args.batch], args.threads,
                             retention='survivors') as batch:
                    native += batch.native_seconds
                    batch_times.append(batch.native_seconds)
                    # Hash the continuous verdict stream, independent of batch partitioning.
                    digest.update(p.ffi.buffer(batch.pointer.verdicts,
                        batch.pointer.count * p.ffi.sizeof('NBVerdict')))
                    survivors += batch.pointer.result_count
                    if batch.pointer.result_count:
                        from seed_search.realm.native_batch import semantic_record
                        for record in batch.retained_records(start + offset):
                            encoded = json.dumps(semantic_record(record), sort_keys=True,
                                                 separators=(',', ':'), allow_nan=False).encode()
                            content.update(len(encoded).to_bytes(8, 'big'))
                            content.update(encoded)
            row = dict(arm=arm, trial=trial, count=args.count, start_index=start,
                       run_key=2026101401, threads=args.threads, chunk=args.chunk, batch=args.batch,
                       native_seconds=native, kernel_rate=args.count/native,
                       process_cpu_seconds=time.process_time()-before_cpu,
                       batch_seconds=batch_times, retained_inputs=survivors,
                       receipt_fingerprint=digest.hexdigest(),
                       survivor_content_fingerprint=content.hexdigest(),
                       receipt_format='continuous native NBVerdict bytes; same ABI required',
                       peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                       build_sha256=p.identity['extension_sha256'])
            rows.append(row)
            digests.append((digest.hexdigest(), content.hexdigest()))
            print(json.dumps(row), flush=True)
            write_json(OUT / args.output, rows)
        if len(set(digests)) > 1:
            raise RuntimeError('Decision or survivor-content mismatch: stop performance evaluation')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'build', 'train', 'merge', 'bench', 'build-diag'))
    parser.add_argument('--allow-heavy', action='store_true')
    parser.add_argument('--arm', choices=ARMS, default='control')
    parser.add_argument('--arms', nargs='+', choices=ARMS, default=['control', 'lazy'])
    parser.add_argument('--chunk', type=int, choices=(16, 64, 128), default=16)
    parser.add_argument('--phase', choices=('training', 'optimized'), default='training')
    parser.add_argument('--threads', type=int, default=34)
    parser.add_argument('--batch', type=int, default=16384)
    parser.add_argument('--count', type=int, default=100000)
    parser.add_argument('--start', type=int, default=51000000)
    parser.add_argument('--trials', type=int, default=3)
    parser.add_argument('--output', default='screen.json')
    args = parser.parse_args()
    if not (1 <= args.batch <= 16384 and 1 <= args.threads <= 34
            and args.count >= 1 and args.start >= 0 and args.trials >= 1):
        parser.error('Invalid bounded batch, thread, cohort, or trial settings')
    if args.action != 'prepare' and not args.allow_heavy:
        parser.error('Heavy work is paused until the user releases this Mac; then pass --allow-heavy')
    if args.action == 'prepare':
        prepare()
    elif args.action == 'build':
        build(args.arm, args.chunk, args.phase)
    elif args.action == 'train':
        train(args.arm, args.chunk)
    elif args.action == 'merge':
        merge(args.arm, args.chunk)
    elif args.action == 'build-diag':
        build_diagnostic()
    else:
        benchmark(args)


if __name__ == '__main__':
    main()
