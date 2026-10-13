"""Resource monitoring must not substitute SELF peak RSS for a process tree."""
import subprocess
from types import SimpleNamespace

import pytest

from seed_search.realm.runner import process_tree_resources


@pytest.mark.parametrize('error',[
    OSError('ps unavailable'),
    subprocess.TimeoutExpired('ps',5),
    subprocess.CalledProcessError(1,'ps'),
])
def test_process_tree_monitor_failure_is_unavailable(monkeypatch,error):
    def fail(*args,**kwargs):
        raise error
    monkeypatch.setattr('seed_search.realm.runner.subprocess.run',fail)
    sample=process_tree_resources(123)
    assert sample['available'] is False
    assert sample['error']
    assert 'rss_bytes' not in sample


def test_process_tree_requires_requested_root_and_includes_descendants(monkeypatch):
    monkeypatch.setattr('seed_search.realm.runner.subprocess.run',
                        lambda *a,**kw:SimpleNamespace(stdout='123 1 100 2\n124 123 200 3\n125 124 300 4\n126 1 900 8\n'))
    sample=process_tree_resources(123)
    assert sample['available'] and sample['rss_bytes']==600*1024
    assert sample['cpu_percent']==9
    assert [r['pid'] for r in sample['processes']]==[123,124,125]
    missing=process_tree_resources(999)
    assert missing['available'] is False


def test_build_rejects_invalid_chunk_before_creating_output(tmp_path):
    from scripts.build_blueprint_batch import build
    path=tmp_path/'invalid'
    for value in (0,32,True,64.0):
        with pytest.raises(ValueError,match='Work chunk'):
            build(path,work_chunk=value)
    assert not path.exists()
