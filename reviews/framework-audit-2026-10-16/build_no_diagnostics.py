import sys,shutil,re,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from scripts import build_blueprint_batch as builder
base=ROOT/'reviews/framework-audit-2026-10-16';snap=base/'no-diag-source'
for name in ('native','vendor/cubiomes-bedrock'):
 shutil.copytree(ROOT/name,snap/name,dirs_exist_ok=True)
(snap/'scripts').mkdir(exist_ok=True)
shutil.copy2(ROOT/'scripts/build_blueprint_batch.py',snap/'scripts/build_blueprint_batch.py')
p=snap/'native/blueprint_dynamic.inc';s=p.read_text()
s,n=re.subn(r'#ifdef _OPENMP\s*#pragma omp atomic\s*#endif\s*g_diag_\w+\+\+;', '',s)
assert n==12,n
p.write_text(s)
builder.ROOT=snap
identity=builder.build(base/'no-diag-build',openmp_prefix=str(ROOT/'runs/master-implementation-2026-10-10/openmp/install'),cpu_native=True,avx2=True,lto=True)
print(json.dumps({'removed_atomic_updates':n,'identity':identity},indent=2))
