"""Independent random+edge BDS world-spawn observations, two isolated worlds at a time."""
import concurrent.futures
import hashlib
import json
import platform
import subprocess
import time
from pathlib import Path
from bds_runner import BASE, ROOT, IMAGE, docker, run_headless


def mix(x):
    mask=2**64-1
    x=((x^(x>>30))*0xbf58476d1ce4e5b9)&mask
    x=((x^(x>>27))*0x94d049bb133111eb)&mask
    return x^(x>>31)


def signed(x):
    return x if x < 2**63 else x-2**64


def main():
    randoms=[signed(mix(i+0x9e3779b97f4a7c15)) for i in range(100)]
    edges=[0,1,-1,-2**63,2**63-1,12345,42,-1234567890123456789]
    seeds=list(dict.fromkeys(randoms+edges))
    (BASE/'seeds.json').write_text(json.dumps({'random':randoms,'edge':edges,'all':seeds},indent=2)+'\n')
    units=['noise','biomes','layers','biomenoise','cave','generator','finders','util','quadbase','mt']
    binary=BASE/'spawn_predict'
    sources=[BASE/'spawn_predict.c']+[ROOT/f'vendor/cubiomes-bedrock/{unit}.c' for unit in units]
    command=['cc','-O3','-std=c11','-fwrapv','-I',str(ROOT/'vendor/cubiomes-bedrock'),*[str(p) for p in sources],'-lm','-o',str(binary)]
    subprocess.run(command,check=True,capture_output=True,text=True,timeout=45)
    run=subprocess.run([str(binary)],input=''.join(str(s)+'\n' for s in seeds),capture_output=True,text=True,check=True,timeout=45)
    predictions=[json.loads(line) for line in run.stdout.splitlines()]
    assert len(predictions)==len(seeds) and [int(p['seed']) for p in predictions]==seeds
    assert all(p['estimate']==p['repeat_estimate'] for p in predictions)
    (BASE/'predictions.json').write_text(json.dumps(predictions,indent=2)+'\n')
    image=docker('image','inspect',IMAGE,'--format','{{.Id}}').stdout.strip()
    identity={'image':IMAGE,'image_id':image,'host':platform.platform(),'compile_command':command,
              'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources+[BASE/'observer.js',BASE/'bds_runner.py',BASE/'run_cohort.py']}}
    (BASE/'identity.json').write_text(json.dumps(identity,indent=2)+'\n')
    started=time.monotonic()
    results=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        pending={pool.submit(run_headless,seed,'cohort-'+str(i).zfill(3)):i for i,seed in enumerate(seeds)}
        for future in concurrent.futures.as_completed(pending):
            row=future.result()
            row['cohort_index']=pending[future]
            results.append(row)
            (BASE/'bds-cohort.json').write_text(json.dumps(sorted(results,key=lambda r:r['cohort_index']),indent=2)+'\n')
            print(json.dumps({'complete':len(results),'total':len(seeds),'seed':row['seed'],'status':row['status'],
                              'default_spawn':row.get('rows',[{}])[-1].get('defaultSpawn') if row.get('rows') else None,
                              'elapsed_seconds':round(time.monotonic()-started,1)}),flush=True)
    assert all(r['status']=='observed' and r['clean_shutdown'] for r in results)
    binary.unlink(missing_ok=True)


if __name__=='__main__':
    main()
