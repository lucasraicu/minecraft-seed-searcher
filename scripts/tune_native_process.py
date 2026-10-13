"""Measure whether spawned preparation pays its owned-record IPC costs."""
import json
import os
from pathlib import Path
import sys
for key in ('OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS'):os.environ[key]='1'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.blueprint_batch_prototype import Prototype
from scripts.native_process_experiment import persist_process_pipeline
from seed_search.realm.config import blueprint_config
if __name__=='__main__':
    p=Prototype(ROOT/'runs/native-throughput-2026-10-12/native',blueprint_config());out=[]
    for threads,batch in ((18,1024),(18,4096),(16,4096)):
        row=persist_process_pipeline(p,ROOT/f'runs/native-throughput-2026-10-12/process-{threads}-{batch}',10000,run_key=120260001000,threads=threads,batch_size=batch)
        out.append(row);(ROOT/'runs/native-throughput-2026-10-12/process-tuning.json').write_text(json.dumps(out,indent=2))
        print(json.dumps({k:row.get(k) for k in ('threads','batch_size','wall_seconds','input_seeds_per_second','native_seconds','record_seconds','prepare_seconds','sql_seconds','commit_seconds')}),flush=True)
