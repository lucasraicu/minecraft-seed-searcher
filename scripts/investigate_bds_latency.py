"""Four isolated tiny-world diagnostics; no finalist/world certification implied."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import statistics
import sys
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from seed_search.realm.config import locked_blueprint_config
from seed_search.realm.verification import VerificationAdapter,tooling_identity
from seed_search.realm.store import canonical
from seed_search.realm.bds_tools import probe_tools, poc_control


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True,type=Path);args=p.parse_args()
    if args.output.exists():p.error('Fresh evidence directory required')
    if shutil.disk_usage(ROOT).free < (20<<30):raise RuntimeError('4 GiB diagnostic growth plus 16 GiB reserve required')
    args.output.mkdir(parents=True)
    original_create=probe_tools.create;rows=[];expected=None;differences=[]
    cfg=locked_blueprint_config();before=tooling_identity()
    for trial in range(2):
        for distance in ([8,5] if trial==0 else [5,8]):
            folder=(args.output/f'view-{distance}-{trial}').resolve();folder.mkdir()
            current_cfg=json.loads(json.dumps(cfg));current_cfg['bds'].update(evidence_dir=str(folder),verification_budget=1)
            def create(name,seed,cpus=4):
                original_create(name,seed,cpus)
                generated=probe_tools.ROOT/(name+'.properties')
                text=generated.read_text().replace('view-distance=8','view-distance='+str(distance))
                generated.write_text(text)
                poc_control.docker('cp',str(generated),name+':/srv/bds/server.properties',capture_output=True,text=True)
                return name
            probe_tools.create=create
            try:
                adapter=VerificationAdapter(current_cfg)
                started=time.perf_counter()
                result=adapter.verify('-1234567890123456789',(-17,-9,15,23),8)
                elapsed=time.perf_counter()-started
                cached_started=time.perf_counter();cached=adapter.verify('-1234567890123456789',(-17,-9,15,23),8)
                cached_seconds=time.perf_counter()-cached_started
                assert cached==result and adapter.used==1
                raw=result.get('evidence',{});fingerprint=hashlib.sha256(canonical(raw.get('columns',[])).encode()).hexdigest()
                row={'trial':trial,'view_distance':distance,'tick_distance':4,'worlds':1,'requested_tiles':1,
                     'requested_columns':16,'wall_seconds':elapsed,'cached_seconds':cached_seconds,
                     'raster_status':result['status'],'raw_status':raw.get('status'),
                     'columns_sha256':fingerprint,'start_seconds':raw.get('start_seconds'),
                     'save_seconds':raw.get('save_seconds'),'coverage':raw.get('coverage'),
                     'resources':raw.get('resources'),'cleanup':raw.get('cleanup'),
                     'diagnostic_overrides':{'view-distance':distance},
                     'promotable_finalist_evidence':False}
                (folder/'observation.json').write_text(json.dumps(result,indent=2)+'\n')
                if not raw or raw.get('status')!='PASS':raise RuntimeError('Diagnostic extraction failed or remained partial: '+canonical(result.get('error',{})))
                if expected is None:expected=raw['columns']
                else:
                    delta=[{'sample':i,'reference':a,'observed':b} for i,(a,b) in enumerate(zip(expected,raw['columns'])) if a!=b]
                    if len(expected)!=len(raw['columns']):delta.append({'column_count':len(raw['columns']),'reference_count':len(expected)})
                    differences.append({'trial':trial,'view_distance':distance,'differences':delta})
                    row['column_differences']=len(delta)
                name=raw['name'];state=poc_control.container_state(name)
                assert state.get('stopped') and state.get('exit_code')==0
                # Remove only these new temporary runtime objects; full snapshots
                # and raw controller reports remain in the fresh evidence folder.
                poc_control.docker('rm',name,capture_output=True,text=True)
                poc_control.docker('volume','rm',name+'-data',capture_output=True,text=True)
                row['temporary_container_and_volume_removed']=True
                rows.append(row);print(json.dumps(row),flush=True)
            finally:probe_tools.create=original_create
    assert tooling_identity()==before,'Pinned production BDS tools changed'
    medians={str(d):statistics.median(r['wall_seconds'] for r in rows if r['view_distance']==d) for d in (8,5)}
    result={'scope':'Counterbalanced tiny 32x32 region, 16 columns, one tile per world; cold setup/start/load/stability/save/clean-stop/snapshot/LevelDB included. Not full 2048-border verification.',
            'worlds':4,'observations':rows,'median_seconds':medians,'view5_speedup':medians['8']/medians['5'],
            'column_differences':sum(len(d['differences']) for d in differences),'differences':differences,'production_tooling_unchanged':True,'production_settings_adopted':False,
            'tooling_identity':before}
    (args.output/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(medians))


if __name__=='__main__':main()
