"""Small reproduction of duplicate strided coverage beyond its 32-bit domain."""
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from seed_search.seeds import seed_strided, seeds_strided
from seed_search.realm.config import dynamic_v3_blueprint_config
from seed_search.realm.native_batch import run_native_scan, seeds_strided_np

assert seed_strided(0, 12345) == seed_strided(2**32, 12345) == 12345
assert seeds_strided(0, 1, 12345) == seeds_strided(2**32, 1, 12345)
assert seeds_strided_np(0, 1, 12345).tolist() == seeds_strided_np(2**32, 2**32 + 1, 12345).tolist()
cfg = dynamic_v3_blueprint_config()
cfg['search'].update(sequence='strided', low32=12345)
with tempfile.TemporaryDirectory(prefix='seed-audit-strided-') as directory:
    result = run_native_scan(cfg, Path(directory) / 'run', count=1, start_index=2**32,
                             native_build=ROOT / 'runs/dynamic-baseline-2048/native',
                             native_threads=1, native_batch_size=1, retention='survivors')
    assert result['completed_seeds'] == 1
    print(json.dumps({'same_seed_at_indices': [0, 2**32], 'seed': 12345,
                      'out_of_domain_completed_seeds': result['completed_seeds']}))
