"""Actual bounded helper processes; never native extraction or live services."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import pytest
from scripts import catalog_validate as cli
from seed_search.catalog.ingestion import ingest,atomic_json,strict_json_loads
from seed_search.catalog.validation_contracts import controls
from tests.catalog.test_ingestion import make_test_build


def test_gated_launch_eof_and_failed_durable_lease_do_not_execute(tmp_path,monkeypatch):
    marker=tmp_path/'executed'
    argv=[sys.executable,'-c',f'from pathlib import Path;Path({str(marker)!r}).touch()']
    child=subprocess.run([sys.executable,'-m','seed_search.catalog.ingestion',json.dumps(argv)],input=b'',capture_output=True,timeout=5)
    assert child.returncode==3 and not marker.exists()
    from seed_search.catalog import ingestion
    original=ingestion.atomic_json
    def fail_lease(path,value):
        if isinstance(value,dict) and value.get('active_lease'):raise OSError('injected durable lease write failure')
        original(path,value)
    monkeypatch.setattr(ingestion,'atomic_json',fail_lease)
    with pytest.raises(OSError,match='injected'):
        ingest(tmp_path/'root',controls(make_test_build()),stop_after=1,command_factory=lambda *_:argv)
    assert not marker.exists()


def test_output_drained_with_bounded_tail_and_complete_checkpoint_checksum(tmp_path):
    build=make_test_build();root=tmp_path/'run'
    def command(_,seed,checkpoint):
        code=(f'from tests.catalog.test_ingestion import make_complete_observation\n'
            f'from seed_search.catalog.ingestion import atomic_json\n'
            f'atomic_json({checkpoint!r},make_complete_observation({seed!r},{build["identity"]!r}))\n'
            'import os;os.write(1,b"x"*200000)\n')
        return [sys.executable,'-c',code]
    report=ingest(root,controls(build),stop_after=1,command_factory=command,poll_seconds=.01)
    receipt=report['receipts'][0]
    assert receipt['status']=='complete' and receipt['output_bytes']==200000
    assert len(receipt['output_tail'])==65536
    def forbidden(*_):raise AssertionError('completed extraction repeated')
    ingest(root,controls(build),resume=True,stop_after=1,command_factory=forbidden)
    with Path(receipt['checkpoint']).open('a') as stream:stream.write(' ')
    with pytest.raises(ValueError,match='checksum'):
        ingest(root,controls(build),resume=True,stop_after=1,command_factory=forbidden)


def supervise_stub(monkeypatch,code):
    frozen=(controls(make_test_build()),{'fixture':'no native extraction'})
    monkeypatch.setattr(cli,'frozen_inputs',lambda:frozen)
    monkeypatch.setattr(cli,'_resources',lambda _:dict(available=True,rss_bytes=1024))
    original=subprocess.Popen
    def popen(args,**kwargs):
        if len(args)>2 and args[1]==str(Path(cli.__file__).resolve()) and args[2]=='_run':
            args=[sys.executable,'-c',code,args[-1]]
        return original(args,**kwargs)
    monkeypatch.setattr(cli.subprocess,'Popen',popen)


def test_supervisor_cumulative_budget_and_stop_reason(tmp_path,monkeypatch):
    supervise_stub(monkeypatch,'import time;time.sleep(.05)')
    output=tmp_path/'normal'
    assert cli.supervise(output)==0
    first=json.loads((output/'job-budget.json').read_text())['charged_seconds']
    assert cli.supervise(output,resume=True)==0
    assert json.loads((output/'job-budget.json').read_text())['charged_seconds']>first
    monkeypatch.undo()
    supervise_stub(monkeypatch,'import time;time.sleep(10)')
    from seed_search.catalog import validation_contracts
    monkeypatch.setattr(validation_contracts,'MAX_JOB_SECONDS',.3)
    output=tmp_path/'cap'
    assert cli.supervise(output)==2
    assert json.loads((output/'supervision.json').read_text())['stop_reason']=='job_wall_cap'
    with pytest.raises(ValueError,match='budget'):cli.supervise(output,resume=True)


def test_supervisor_fails_closed_without_aggregate_monitor(tmp_path,monkeypatch):
    supervise_stub(monkeypatch,'import time;time.sleep(10)')
    monkeypatch.setattr(cli,'_resources',lambda _:dict(available=False))
    with pytest.raises(RuntimeError,match='RSS monitoring'):cli.supervise(tmp_path/'unknown-rss')


def test_sigkill_parent_lifeline_stops_owned_child(tmp_path):
    # The child here follows the CLI's lifeline contract without importing any
    # extractor. SIGKILL cannot execute finally in the supervisor.
    root=tmp_path/'job';marker=tmp_path/'child.json';ended=tmp_path/'ended'
    code=f'''
import os,json,sys,subprocess
from pathlib import Path
from scripts import catalog_validate as cli
from seed_search.catalog.validation_contracts import controls
from tests.catalog.test_ingestion import make_test_build
cli.frozen_inputs=lambda:(controls(make_test_build()),{{'fixture':'lifeline'}})
cli._resources=lambda _:dict(available=True,rss_bytes=1024)
original=subprocess.Popen
def launch(args,**kwargs):
    if len(args)>2 and args[2]=='_run':
        stub="import os,sys,json;from pathlib import Path;Path({str(marker)!r}).write_text(json.dumps({{'pid':os.getpid()}}));os.read(int(sys.argv[1]),1);Path({str(ended)!r}).touch()"
        args=[sys.executable,'-c',stub,args[-1]]
    return original(args,**kwargs)
cli.subprocess.Popen=launch
cli.supervise(Path({str(root)!r}))
'''
    parent=subprocess.Popen([sys.executable,'-c',code],start_new_session=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        deadline=time.monotonic()+10
        while not marker.exists() and time.monotonic()<deadline:
            if parent.poll() is not None:raise AssertionError(parent.communicate())
            time.sleep(.01)
        assert marker.exists()
        parent.kill();parent.wait(timeout=5)
        deadline=time.monotonic()+5
        while not ended.exists() and time.monotonic()<deadline:time.sleep(.01)
        assert ended.exists()
        assert json.loads((root/'job-budget.json').read_text())['charged_seconds']==60
    finally:
        if parent.poll() is None:parent.kill();parent.wait(timeout=5)
        if marker.exists() and not ended.exists():
            try:os.kill(json.loads(marker.read_text())['pid'],signal.SIGKILL)
            except ProcessLookupError:pass
        parent.stdout.close();parent.stderr.close()
