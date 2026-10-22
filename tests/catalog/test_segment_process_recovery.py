"""Kill an owned segmented publisher at real SQLite publication boundaries."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import pytest
from seed_search.catalog.segments import SegmentedCatalog
from tests.catalog.test_segments import make_synthetic_obs, make_synthetic_summary


@pytest.mark.parametrize('boundary', ['before_commit', 'after_commit'])
def test_segment_writer_death_preserves_pinned_readers_and_replays(tmp_path, boundary):
    root = tmp_path / 'pilot'
    first = make_synthetic_obs(0)
    second = make_synthetic_obs(1)
    with SegmentedCatalog(root) as store:
        old = store.publish([first], [make_synthetic_summary(first)])
    fixture = tmp_path / 'input.json'
    fixture.write_text(json.dumps([second, make_synthetic_summary(second)]))
    marker = tmp_path / 'ready'
    script = tmp_path / 'writer.py'
    script.write_text('''import json,os,sys,time
from pathlib import Path
from seed_search.catalog.segments import SegmentedCatalog
root,fixture,marker,boundary,parent=sys.argv[1:]
obs,row=json.loads(Path(fixture).read_text())
def gate():
 with open(marker,'w') as out:out.write('ready');out.flush();os.fsync(out.fileno())
 while True:time.sleep(0.05)
with SegmentedCatalog(root) as store:
 if boundary=='before_commit':
  store.conn.create_function('crash_gate',0,gate)
  store.conn.execute('CREATE TEMP TRIGGER crash_boundary BEFORE INSERT ON snapshot_root BEGIN SELECT crash_gate(); END;')
 store.publish([obs],[row],parent=parent)
 if boundary=='after_commit':gate()
''')
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1',
               PYTHONPATH=str(Path(__file__).resolve().parents[2] / 'src'))
    child = subprocess.Popen([sys.executable, str(script), str(root), str(fixture),
                              str(marker), boundary, old], env=env)
    try:
        deadline = time.monotonic() + 15
        while not marker.exists() and child.poll() is None and time.monotonic() < deadline:
            time.sleep(0.02)
        assert marker.exists(), 'Owned writer did not reach its declared kill boundary'
        with SegmentedCatalog(root) as reader:
            assert reader.audit(old)['worlds'] == 1
            assert len(reader.snapshots()) == (1 if boundary == 'before_commit' else 2)
        child.kill()
        child.wait(timeout=5)
        assert child.returncode < 0
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=5)
    with SegmentedCatalog(root) as recovered:
        parent = recovered.info()['snapshot_id']
        sid = recovered.publish([second], [make_synthetic_summary(second)], parent=parent)
        assert recovered.audit(old)['worlds'] == 1
        assert recovered.audit(sid)['worlds'] == 2
        assert len(recovered.snapshots()) == 2
        recovered.backup(tmp_path / 'restored')
    with SegmentedCatalog(tmp_path / 'restored') as restored:
        assert restored.audit(sid)['worlds'] == 2
        assert restored.observation(sid, make_synthetic_summary(second)['world_id']) == second
