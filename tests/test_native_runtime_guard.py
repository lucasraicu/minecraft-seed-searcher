"""Real import-order regression plus isolated fake native handles and cache checks."""
import os
from pathlib import Path
import subprocess
import sys
import threading

import pytest

from seed_search import backend
from seed_search.realm import native_identity as identity


class FakeFFI:
    NULL = None

    def string(self, ptr):
        return ptr

    def gc(self, ptr, destroy):
        return ptr

    def release(self, ptr):
        pass


class FakeLib:
    def __init__(self, digest=b'a'*64):
        self.digest = digest
        self.creates = 0

    def ss_source_fingerprint(self):
        return self.digest

    def ss_create(self, seed):
        self.creates += 1
        return object()

    def ss_destroy(self, ptr):
        pass

    def ss_openmp_enabled(self):
        return 0

    def ss_openmp_library(self):
        return None


@pytest.fixture
def runtime(monkeypatch):
    monkeypatch.setattr(identity, '_VALIDATED_RUNTIMES', {})
    monkeypatch.setattr(identity, 'native_source_fingerprint', lambda: 'a'*64)
    ffi,lib = FakeFFI(),FakeLib()
    monkeypatch.setattr(backend, 'ffi', ffi)
    monkeypatch.setattr(backend, 'lib', lib)
    return ffi,lib


def test_stale_direct_backend_and_entry_points_fail_before_native_work(runtime):
    ffi,lib=runtime
    lib.digest=b'b'*64
    for operation in (lambda: backend.Backend(1),backend.biome_catalog,
                      lambda: backend.raw_layout(0,'village',(0,0,16,16)),
                      lambda: backend.sweep_raw(0,1,[('village',(0,0,16,16))])):
        with pytest.raises(ValueError,match='rebuild the active engine'):
            operation()
    assert lib.creates==0 and identity._VALIDATED_RUNTIMES=={}


def test_1000_handles_and_cached_handle_use_hash_sources_once(runtime,monkeypatch):
    calls=[]
    monkeypatch.setattr(identity,'native_source_fingerprint',lambda: calls.append(1) or 'a'*64)
    for seed in range(1000):
        with backend.Backend(seed) as b:
            b._handle()
    assert calls==[1] and runtime[1].creates==1000


def test_explicit_job_preflight_revalidates_and_blocks_existing_and_new_handles(runtime,monkeypatch):
    ffi,lib=runtime
    b=backend.Backend(1)
    assert backend.native_runtime()=={'openmp':False,'runtime_sha256':None,'policy':'outer-columns-static-min256-v1'}
    # Source edits are checked at explicit job boundaries, not polled per seed.
    monkeypatch.setattr(identity,'native_source_fingerprint',lambda: 'b'*64)
    with pytest.raises(ValueError):backend.native_runtime()
    assert identity._VALIDATED_RUNTIMES=={}
    with pytest.raises(ValueError):b._handle()
    with pytest.raises(ValueError):backend.Backend(2)
    assert lib.creates==1
    b.close()


@pytest.mark.parametrize('digest',[None,b'',b'a'*63,b'g'*64,b'\xff'*64])
def test_wheel_requires_well_formed_embedded_identity(runtime,monkeypatch,digest):
    ffi,lib=runtime
    monkeypatch.setattr(identity,'native_source_fingerprint',lambda: None)
    lib.digest=digest
    with pytest.raises(ValueError):identity.ensure_runtime_validated(ffi,lib)
    assert not identity._VALIDATED_RUNTIMES
    lib.digest=b'0'*64
    identity.ensure_runtime_validated(ffi,lib)


def test_missing_identity_never_caches_success(runtime):
    with pytest.raises(ValueError):identity.ensure_runtime_validated(runtime[0],object())
    assert not identity._VALIDATED_RUNTIMES


def test_cache_pins_objects_and_separates_pid_and_library(runtime,monkeypatch):
    ffi,lib=runtime
    identity.ensure_runtime_validated(ffi,lib)
    assert list(identity._VALIDATED_RUNTIMES.values())==[(ffi,lib)]
    lib2=FakeLib(b'b'*64)
    with pytest.raises(ValueError):identity.ensure_runtime_validated(ffi,lib2)
    pid=os.getpid()
    monkeypatch.setattr(identity.os,'getpid',lambda:pid+1)
    lib.digest=b'b'*64
    with pytest.raises(ValueError):identity.ensure_runtime_validated(ffi,lib)


def test_forced_preflight_cannot_race_a_cached_constructor(runtime,monkeypatch):
    ffi,lib=runtime
    identity.ensure_runtime_validated(ffi,lib)
    started=threading.Event();release=threading.Event();finished=threading.Event();errors=[]
    def changed_source():
        started.set()
        assert release.wait(5)
        return 'b'*64
    monkeypatch.setattr(identity,'native_source_fingerprint',changed_source)
    def preflight():
        try:identity.validate_compiled_sources(ffi,lib)
        except ValueError:errors.append('preflight')
    def construct():
        try:backend.Backend(1)
        except ValueError:errors.append('constructor')
        finally:finished.set()
    first=threading.Thread(target=preflight);second=threading.Thread(target=construct)
    first.start()
    assert started.wait(5)
    second.start()
    assert not finished.wait(.03)
    release.set();first.join(5);second.join(5)
    assert not first.is_alive() and not second.is_alive()
    assert sorted(errors)==['constructor','preflight'] and lib.creates==0


def test_helper_first_import_order_in_fresh_process():
    script=r'''
import sys,types
before=list(sys.path)
import scripts.predictor_storage_probe as storage
assert sys.path==before, 'storage helper changed runtime import precedence'
class FFI:
 NULL=None
 def string(self,p):return p
 def gc(self,p,d):return p
 def release(self,p):pass
class Lib:
 digest=b'0'*64
 creates=0
 def ss_source_fingerprint(self):return self.digest
 def ss_create(self,seed):self.creates+=1;return object()
 def ss_destroy(self,p):pass
 def ss_openmp_enabled(self):return 0
 def ss_openmp_library(self):return None
native=types.ModuleType('seed_search._native');native.ffi=FFI();native.lib=Lib()
sys.modules['seed_search._native']=native
from seed_search.backend import Backend,native_runtime
from seed_search.realm.native_identity import native_source_fingerprint
try:Backend(1)
except ValueError:pass
else:raise AssertionError('stale handle accepted')
assert native.lib.creates==0
native.lib.digest=native_source_fingerprint().encode()
with Backend(1):pass
assert native.lib.creates==1
assert native_runtime()['policy']=='outer-columns-static-min256-v1'
print('helper-first runtime rejected then validated')
'''
    result=subprocess.run([sys.executable,'-c',script],cwd=Path(__file__).resolve().parents[1],
        capture_output=True,text=True,timeout=20)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'helper-first runtime rejected then validated' in result.stdout


@pytest.mark.skipif(not hasattr(os,'fork'),reason='fork unavailable')
def test_fork_resets_lock_and_runtime_validation(runtime):
    ffi,lib=runtime
    identity.ensure_runtime_validated(ffi,lib)
    acquired=threading.Event();release=threading.Event()
    def hold():
        with identity._VALIDATION_LOCK:
            acquired.set();release.wait(10)
    thread=threading.Thread(target=hold);thread.start();assert acquired.wait(5)
    pid=os.fork()
    if pid==0:
        import signal
        signal.alarm(3)
        lib.digest=b'b'*64
        try:identity.ensure_runtime_validated(ffi,lib)
        except ValueError:os._exit(0)
        os._exit(1)
    try:
        _,status=os.waitpid(pid,0)
        assert os.waitstatus_to_exitcode(status)==0
    finally:
        release.set();thread.join(5)
