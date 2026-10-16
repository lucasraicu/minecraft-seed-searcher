import sys,shutil,json,re,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from scripts import build_blueprint_batch as builder
base=Path(__file__).resolve().parent;snap=base/'source'
for name in ('native','vendor/cubiomes-bedrock'):
 shutil.copytree(ROOT/name,snap/name,dirs_exist_ok=True)
(snap/'scripts').mkdir(exist_ok=True);shutil.copy2(ROOT/'scripts/build_blueprint_batch.py',snap/'scripts/build_blueprint_batch.py')
builder.ROOT=snap
p=snap/'native/blueprint_dynamic.inc';original=p.read_text()
(base/'source-hashes.json').write_text(json.dumps({str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for folder in ('native','src/seed_search/realm') for f in (ROOT/folder).glob('*') if f.is_file()},indent=2))
for arm in ('baseline','order','chunk64','no-preflight'):
 s=original
 if arm=='order':s=s.replace('const int slots[5]={12,0,6,4,5};','const int slots[5]={0,4,6,5,12};')
 # Disabled preflight must still initialize Phase1 before Phase2.
 if arm=='no-preflight':s=s.replace('applySeedPhase2(&w->ctx->overworld,DIM_OVERWORLD,seed);','applySeedPhase1(&w->ctx->overworld,DIM_OVERWORLD,seed);\n            applySeedPhase2(&w->ctx->overworld,DIM_OVERWORLD,seed);')
 p.write_text(s)
 identity=builder.build(base/arm,openmp_prefix=str(ROOT/'runs/master-implementation-2026-10-10/openmp/install'),cpu_native=True,avx2=True,lto=True,work_chunk=64 if arm=='chunk64' else 16,dynamic_preflight=arm!='no-preflight')
 print(arm,identity['extension_sha256'],flush=True)
p.write_text(original)
