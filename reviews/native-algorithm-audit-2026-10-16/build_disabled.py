import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));from scripts import build_blueprint_batch as builder
base=Path(__file__).resolve().parent;builder.ROOT=base/'source'
print(json.dumps(builder.build(base/'disabled-unfixed',openmp_prefix=str(ROOT/'runs/master-implementation-2026-10-10/openmp/install'),cpu_native=True,avx2=True,lto=True,dynamic_preflight=False)))
