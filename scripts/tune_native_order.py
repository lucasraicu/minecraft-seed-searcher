"""Bounded paired experiment of SQLite insert locality; complete evidence retained."""
import json,os,time,sys,argparse
from pathlib import Path
for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[name]='1'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from seed_search.realm.native_batch import Prototype,persist_pipeline
from seed_search.realm.config import blueprint_config
from seed_search.realm.store import RealmStore,_restore_prepared
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
original=RealmStore.complete_prepared;rows=[]
def local(self,prepared,**kw):
    fields=[]
    for name in prepared.__dataclass_fields__:
        if name=='_token':continue
        value=getattr(prepared,name)
        if name in ('candidate_rows','inventory_rows','variant_rows'):value=tuple(sorted(value))
        fields.append(value)
    return original(self,_restore_prepared(tuple(fields)),**kw)
prototype=Prototype(ROOT/'runs/native-throughput-2026-10-12/native-final',blueprint_config())
for trial in range(3):
    for arm in (('original','sorted') if trial%2==0 else ('sorted','original')):
        RealmStore.complete_prepared=original if arm=='original' else local
        r=persist_pipeline(prototype,a.output/f'{arm}-{trial}',10000,run_key=120260001000,threads=16,batch_size=4096)
        r.update(trial=trial,arm=arm);rows.append(r);print(json.dumps({k:r[k] for k in ('arm','trial','wall_seconds','input_seeds_per_second','sql_seconds','commit_seconds')}),flush=True)
        (a.output/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
