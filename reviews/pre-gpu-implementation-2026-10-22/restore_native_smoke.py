"""Relocate only copied native metadata; preserve archived bytes and content pins."""
from pathlib import Path
import os,sys,json,shutil,hashlib,subprocess
R=Path(__file__).resolve().parents[2];E=Path(__file__).parent;B=Path.home()/'.local/share/antigravity-worker-mcp/pre-gpu-readiness-approved-20261022';reference=B/'reference';old=reference/'runs/dynamic-baseline-2048/native-corrected-openmp-2026-10-21';identity=json.loads((old/'identity.json').read_text());target=B/'relocated-native-build';target.mkdir()
original_identity_hash=hashlib.sha256((old/'identity.json').read_bytes()).hexdigest();binary=old/Path(identity['extension']).name
assert hashlib.sha256(binary.read_bytes()).hexdigest()==identity['extension_sha256']
shutil.copy2(binary,target/binary.name);runtime=Path(identity['runtime']);assert hashlib.sha256(runtime.read_bytes()).hexdigest()==identity['runtime_sha256'];shutil.copy2(runtime,B/'runtime-libomp.dylib')
new=dict(identity,extension=str(target/binary.name));(target/'identity.json').write_text(json.dumps(new,indent=2)+'\n')
assert {k:v for k,v in new.items()if k!='extension'}=={k:v for k,v in identity.items()if k!='extension'}
code='''from pathlib import Path
import json,sys
import seed_search.catalog.store as store
from seed_search.realm.config import dynamic_v3_blueprint_config
from seed_search.realm.native_batch import Prototype
reference=Path(sys.argv[1]);p=Prototype(sys.argv[2],dynamic_v3_blueprint_config())
assert Path(store.__file__).is_relative_to(reference)
assert Path(p.module.__file__).is_relative_to(Path(sys.argv[2]))
print(json.dumps(dict(catalog_module=store.__file__,native_module=p.module.__file__,native_identity=p.identity)))
'''
r=subprocess.run([sys.executable,'-c',code,str(reference),str(target)],cwd=reference,env=dict(os.environ,PYTHONPATH=str(reference/'src'),PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True,timeout=20);assert r.returncode==0,r.stderr
assert hashlib.sha256((old/'identity.json').read_bytes()).hexdigest()==original_identity_hash
report=dict(status='PASS',**json.loads(r.stdout),relocated_locator_only=True,archived_identity_unchanged=True,libomp_copy_sha256=hashlib.sha256((B/'runtime-libomp.dylib').read_bytes()).hexdigest(),scope='Fresh isolated source/custom native build import with explicit copied extension-locator rebind. All content/source/runtime hashes remain pinned. External host OpenMP path is still verified;no native rebuild/binary patch or seed search')
(E/'RESTORE_NATIVE_SMOKE.json').write_text(json.dumps(report,indent=2)+'\n');print('Isolated custom native/source restore PASS')
