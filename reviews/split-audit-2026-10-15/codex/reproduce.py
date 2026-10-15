"""Targeted final-review reproductions; no end-to-end pipeline execution."""
import contextlib, gc, importlib.util, io, json, os, resource, runpy, subprocess, sys, tempfile, types, weakref
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
OUT=ROOT/'reviews/split-audit-2026-10-15/codex'
G=ROOT/'reviews/split-audit-2026-10-15/gemini'
records=[]
def run(name, function):
 stream=io.StringIO()
 try:
  with contextlib.redirect_stdout(stream):result=function()
  row={'id':name,'status':'completed','result':result,'stdout':stream.getvalue()}
 except BaseException as exc:
  row={'id':name,'status':'error','error':repr(exc),'stdout':stream.getvalue()}
 records.append(row);(OUT/'reproductions.json').write_text(json.dumps(records,indent=2)+'\n')
 print(name,row['status'],str(row.get('result',row.get('error')))[:600],flush=True)
def gemini(name, file, func):
 def call():
  ns=runpy.run_path(str(G/file))
  with tempfile.TemporaryDirectory(prefix='codex-final-') as td:return ns[func](Path(td))
 run(name,call)

gemini('G-STORE-02','probes/store/probe_toctou_lease_overwrite.py','test_toctou_lease_overwrite_and_double_counting')
gemini('G-STORE-03','probes/store/probe_complete_range_no_lease.py','test_complete_range_bypasses_lease')
gemini('G-STORE-05','probes/store/probe_web_server_lock_starvation.py','test_pause_sweep_lock_starvation')
gemini('G-STORE-07','probes/store/probe_connection_thread_confinement.py','test_thread_confinement_and_preparation')

def owner_lock():
 from seed_search.realm.runner import _scan_lock
 with tempfile.TemporaryDirectory() as td:
  code='from seed_search.realm.runner import _scan_lock\nimport sys\nwith _scan_lock(sys.argv[1]):print("ACQUIRED")'
  with _scan_lock(td):
   p=subprocess.run([sys.executable,'-c',code,td],capture_output=True,text=True)
  assert p.returncode!=0 and 'Another Realm scanner owns this run' in p.stderr
  return {'second_scanner_blocked':True,'returncode':p.returncode,'error':p.stderr.strip()}
run('single-scanner-owner-contract',owner_lock)

def allocation_checks():
 sys.path.insert(0,'/tmp/minecraft-audit-20261015')
 import audit_batch as a
 from seed_search.realm.native_batch import Prototype,Batch
 from seed_search.realm.config import dynamic_blueprint_config
 p=Prototype(ROOT/'runs/dynamic-baseline-1664/native',dynamic_blueprint_config())
 policy=a.ffi.new('NBPolicy *');a.ffi.buffer(policy)[:]=bytes(p.ffi.buffer(p.policy));policy.retention=1;policy.max_misses=2
 seeds=a.ffi.new('uint64_t[]',[123]);fixtures=a.ffi.new('NBFixture[]',[(0,0,-1,0,1)])
 cases=[]
 for cap,fail in [(1400000,0),(268435456,35)]:
  policy.max_buffer_bytes=cap;a.lib.audit_reset(fail)
  b=a.lib.nb_fixture_sweep(seeds,fixtures,1,policy,1)
  assert b!=a.ffi.NULL
  row=dict(cap=cap,failed_allocation=fail,error=b.error,peak=a.lib.audit_peak(),live_before_free=a.lib.audit_live())
  a.lib.nb_free(b);row['live_after_free']=a.lib.audit_live();assert row['live_after_free']==0;cases.append(row)
 # Demonstrate unmanaged Batch lifetime without leaking the probe's allocation.
 policy.max_buffer_bytes=268435456;a.lib.audit_reset(0)
 pointer=a.lib.nb_fixture_sweep(seeds,fixtures,1,policy,1)
 batch=Batch(types.SimpleNamespace(lib=a.lib),pointer,[123],0,False,True,'survivors',2)
 ref=weakref.ref(batch);del batch;gc.collect()
 footgun=dict(batch_collected=ref() is None,live_after_collection=a.lib.audit_live())
 a.lib.nb_free(pointer);footgun['live_after_explicit_free']=a.lib.audit_live()
 return dict(allocation_cases=cases,unmanaged_batch=footgun)
run('G-MEM-02-G-MEM-05-G-FFI-04',allocation_checks)

def crashes():
 resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 rows=[]
 for failure in (34,35,36):
  p=subprocess.run([sys.executable,'/tmp/minecraft-audit-20261015/probe.py','268435456',str(failure),'2'],capture_output=True,text=True)
  rows.append(dict(allocation=failure,returncode=p.returncode,stderr=p.stderr.strip()))
  assert p.returncode==-11
 return rows
run('G-MEM-01',crashes)

def patches():
 rows=[]
 for patch in sorted((G/'proposals').glob('*.patch')):
  p=subprocess.run(['git','apply','--check',str(patch)],cwd=ROOT,capture_output=True,text=True)
  rows.append(dict(patch=patch.name,applies=p.returncode==0,error=p.stderr.strip()))
 return rows
run('gemini-patch-applicability',patches)

def optional():
 p=subprocess.run([sys.executable,str(ROOT/'reviews/codex-audit-2026-10-15/probes/optional_probe.py')],cwd=ROOT,capture_output=True,text=True,env={**os.environ,'PYTHONPATH':str(ROOT)+':'+str(ROOT/'src')})
 assert p.returncode==0,p.stderr
 return {'stdout':p.stdout,'returncode':p.returncode}
run('G-GEO-01',optional)
