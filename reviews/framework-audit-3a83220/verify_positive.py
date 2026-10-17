"""Independent positive-path audit; does not modify application state."""
import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from seed_search.realm.blueprint import evaluate_dynamic_seed
from seed_search.realm.config import dynamic_v3_blueprint_config
from seed_search.realm.native_batch import Prototype
from seed_search.realm.reports import _candidate_rescore

SEED = -3336796033057908633


def view(anchor):
    return {key: anchor.get(key) for key in (
        'evaluation_center', 'baseline_score_observed', 'radial_key',
        'origin_distance_squared', 'hub_bonus', 'scenic_bonus',
        'village_spread_bonus', 'ranking')}


def main():
    cfg = dynamic_v3_blueprint_config()
    cfg['biomes']['required_families'] = []
    rows = {'scope': 'Natural structure-floor survivor with CUSTOM EMPTY Overworld palette; not a default-blueprint survivor', 'seed': SEED}
    current = ROOT / 'runs/dynamic-baseline-2048/native'
    p = Prototype(current, cfg)
    rows['native_identity'] = p.identity
    anchors = {}
    for retention in ('full', 'survivors'):
        with p.sweep([SEED], threads=1, retention=retention) as batch:
            records = batch.records() if retention == 'full' else list(batch.retained_records())
            anchor = records[0]['anchors'][0]
            anchors[retention] = anchor
            rows[retention] = view(anchor)
    reference = evaluate_dynamic_seed(0, SEED, cfg, short_circuit=False)
    rows['independent_python'] = view(reference['anchors'][0])
    rescored = _candidate_rescore(copy.deepcopy(anchors['full']), cfg, 'audit-current-3a83220')
    rows['rescore'] = view(rescored)
    keys = ('evaluation_center', 'baseline_score_observed', 'radial_key', 'origin_distance_squared')
    expected = rows['full']
    for route in ('survivors', 'independent_python', 'rescore'):
        for key in keys:
            assert rows[route][key] == expected[key], (route, key, rows[route][key], expected[key])
    for cutoff in (expected['baseline_score_observed'], expected['baseline_score_observed'] + 1):
        with p.sweep([SEED], threads=1, retention='survivors', cutoff_score=cutoff) as batch:
            rows[f'cutoff_{cutoff}_retained'] = int(batch.pointer.result_count)
    rows['stale_builds'] = []
    for directory in [ROOT / 'runs/dynamic-baseline-2048/native-mansion-bound-2026-10-16']:
        identity = json.loads((directory / 'identity.json').read_text())
        stale = [name for name, digest in identity['inputs'].items()
                 if (ROOT / name).exists() and hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest]
        item = {'directory': str(directory), 'stale_inputs': stale}
        try:
            old = Prototype(directory, dynamic_v3_blueprint_config())
            with old.sweep([456], fixtures=[(0, 0, -1)]) as batch:
                item['fixture'] = view(batch.records()[0]['anchors'][0])
        except Exception as exc:
            item['exception'] = f'{type(exc).__name__}: {exc}'
        rows['stale_builds'].append(item)
    output = Path(__file__).with_name('positive.json')
    output.write_text(json.dumps(rows, indent=2) + '\n')
    print(json.dumps({key: value for key, value in rows.items() if key not in ('native_identity',)}, indent=2))


if __name__ == '__main__':
    main()
