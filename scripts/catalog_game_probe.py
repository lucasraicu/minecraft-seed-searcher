#!/usr/bin/env python3
"""Bounded, isolated BDS surface-point evidence; never certifies catalog structures."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
import uuid

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
DOCKER='/Users/lucasraicu/.docker/bin/docker'


def run(output,seed,*,seconds=1200):
    from seed_search.catalog.ingestion import atomic_json,tree_bytes,verify_no_symlinks
    from seed_search.realm import verification as v
    from seed_search.realm.bds_tools import probe_tools as p,poc_control as c
    if type(seconds) is not int or not 1<=seconds<=1200:raise ValueError('Probe allowance must be1..1200 seconds')
    output=verify_no_symlinks(output);output.mkdir(parents=True,exist_ok=False)
    token='catalog-probe-'+uuid.uuid4().hex
    label='seed-search.catalog-probe='+token
    started=time.monotonic();deadline=started+seconds
    volumes=set();containers=set();gate=threading.Lock();done=threading.Event();stop_reason=[]
    original=c.docker;c.DOCKER=DOCKER
    if v.CLEANUP_GUARD.exists():
        atomic_json(output/'report.json',dict(status='BLOCKED',reason='Existing verifier cleanup guard requires owner review; no world created'))
        return 2
    v.CLEANUP_GUARD=output/'cleanup-guard.json'
    def direct(*args,**kw):
        kw.setdefault('timeout',30)
        return subprocess.run([DOCKER,*args],check=True,**kw)
    def owned(*args,**kw):
        args=list(args)
        if args[:2]==['volume','create']:
            name=args[-1]
            exists=subprocess.run([DOCKER,'volume','inspect',name],capture_output=True,timeout=15)
            if exists.returncode==0:raise RuntimeError('Refusing existing volume')
            args[2:2]=['--label',label]
            with gate:
                result=original(*args,**kw)
                volumes.add(name)
                atomic_json(output/'owned.json',dict(label=label,volumes=sorted(volumes),containers=sorted(containers)))
            return result
        elif args and args[0] in ('create','run'):
            if args[0]=='create':
                name=args[args.index('--name')+1]
                exists=subprocess.run([DOCKER,'inspect',name],capture_output=True,timeout=15)
                if exists.returncode==0:raise RuntimeError('Refusing existing container')
                with gate:containers.add(name)
                # BDS stops even if this Python process dies. The image stays pinned.
                remaining=max(1,int(deadline-time.monotonic()-30))
                image_index=args.index(v.IMAGE)
                args[image_index+1:]=['--signal=TERM','--kill-after=15',str(remaining),'/opt/entrypoint.sh']
                args[1:1]=['--entrypoint','/usr/bin/timeout','--network','bridge','--label',label,
                    '--read-only','--tmpfs','/tmp:rw,size=64m','--ulimit','core=0',
                    '--log-opt','max-size=10m','--log-opt','max-file=2']
                atomic_json(output/'owned.json',dict(label=label,volumes=sorted(volumes),containers=sorted(containers)))
            else:
                args[1:1]=['--network','none','--cpus','1','--memory','256m','--label',label,
                    '--read-only','--tmpfs','/tmp:rw,size=64m','--ulimit','core=0',
                    '--log-opt','max-size=10m','--log-opt','max-file=2']
        return original(*args,**kw)
    def interrupt(*_):raise TimeoutError(stop_reason[0] if stop_reason else 'Cumulative game allowance exhausted')
    old_handler=signal.signal(signal.SIGALRM,interrupt);watcher=None
    def monitor():
        while not done.wait(5):
            try:
                total=tree_bytes(output)
                with gate:names=sorted(volumes)
                for name in names:
                    data=direct('volume','inspect',name,capture_output=True,text=True)
                    record=json.loads(data.stdout)[0]
                    if (record.get('Labels') or {}).get('seed-search.catalog-probe')!=token:
                        raise RuntimeError('Owned-volume label mismatch')
                    measured=direct('run','--rm','--network','none','--cpus','1','--memory','128m','--label',label,
                        '--entrypoint','/usr/bin/du','--mount',f'type=volume,src={name},dst=/owned,readonly',v.IMAGE,'-sb','/owned',capture_output=True,text=True)
                    total+=int(measured.stdout.split()[0])
                atomic_json(output/'resource-sample.json',dict(owned_bytes=total,wall_seconds=time.monotonic()-started))
                if total>8<<30:raise RuntimeError('Owned Docker/host output allowance8GiB exceeded')
            except Exception as error:
                if not done.is_set():stop_reason.append(str(error));os.kill(os.getpid(),signal.SIGALRM)
                return
    report=dict(schema='catalog-game-point-probe-v1',seed=str(seed),label=label,status='not_completed',
        structure_certification=False,spawn_certification=False,compatibility_acceptance=False)
    cleanup=[]
    try:
        image=json.loads(direct('image','inspect',v.IMAGE,capture_output=True,text=True).stdout)[0]
        if image['Id']!=v.IMAGE_ID:raise ValueError('Installed BDS image digest mismatch')
        direct('run','--rm','--network','none','--read-only','--cpus','1','--memory','128m','--label',label,
               '--entrypoint','/usr/bin/timeout',v.IMAGE,'--version',capture_output=True,text=True)
        c.docker=p.docker=owned
        adapter=v.VerificationAdapter({'bds':dict(enabled=True,docker_cli=DOCKER,verification_budget=1,
            persist_snapshot=False,compare_reference=False,evidence_dir=str(output),max_tiles_per_request=16)})
        points=[(x,z) for x in (-256,0,256,512) for z in (-256,0,256,512)]
        atomic_json(output/'controls.json',dict(seed=str(seed),points=points,image_id=v.IMAGE_ID,
            seconds=seconds,owned_output_bytes=8<<30,container_cpus=4,container_memory_gib=6,
            network='bridge',published_ports=[],
            purpose='Actual surface points, distinct from fixed-Y63 catalog witnesses'))
        signal.alarm(seconds);watcher=threading.Thread(target=monitor,daemon=True);watcher.start()
        result=adapter.verify_surface_points(seed,points,selection_reason='explicit')
        report.update(status=result['status'],result=result)
        # Compare the predictor at OBSERVED Y, not the catalog's different Y63 predicate.
        from seed_search.backend import Backend
        comparisons=[]
        with Backend(int(seed)) as backend:
            for row in result.get('surface_biome_observations',[]):
                if row.get('status')=='OBSERVED':
                    comparisons.append(dict(observed=row,predicted=backend.biome(row['x'],row['y'],row['z'])))
        report['same_coordinate_y_comparisons']=comparisons
    except Exception as error:
        report.update(status='FAILED',error=type(error).__name__+': '+str(error))
    finally:
        signal.alarm(0);signal.signal(signal.SIGALRM,lambda *_:None);done.set()
        if watcher is not None:watcher.join(timeout=100)
        c.docker=p.docker=original
        try:
            discovered=direct('ps','--all','--filter','label='+label,'--format','{{.Names}}',capture_output=True,text=True)
            containers.update(name for name in discovered.stdout.splitlines() if name)
        except Exception as error:cleanup.append(dict(discovery_error=str(error)))
        # Only exact resources tagged by this invocation are eligible for cleanup.
        for name in sorted(containers):
            try:
                data=json.loads(direct('inspect',name,capture_output=True,text=True).stdout)[0]
                if (data.get('Config',{}).get('Labels') or {}).get('seed-search.catalog-probe')!=token:
                    raise RuntimeError('Container ownership mismatch; cleanup refused')
                direct('rm','--force',name,capture_output=True,text=True)
                cleanup.append(dict(container=name,removed=True))
            except Exception as error:cleanup.append(dict(container=name,error=str(error)))
        for name in sorted(volumes):
            try:
                data=json.loads(direct('volume','inspect',name,capture_output=True,text=True).stdout)[0]
                if (data.get('Labels') or {}).get('seed-search.catalog-probe')!=token:
                    raise RuntimeError('Volume ownership mismatch; cleanup refused')
                direct('volume','rm',name,capture_output=True,text=True)
                cleanup.append(dict(volume=name,removed=True))
            except Exception as error:cleanup.append(dict(volume=name,error=str(error)))
        signal.signal(signal.SIGALRM,old_handler)
        report.update(cleanup=cleanup,wall_seconds=time.monotonic()-started,
            note='Scoped surface observations only. Fixed-Y63 witnesses, generated structures, and spawn remain unaccepted.')
        atomic_json(output/'report.json',report)
    print(json.dumps({k:report[k] for k in ('status','wall_seconds','cleanup')},indent=2))
    return 0 if report['status']!='FAILED' and all(r.get('removed') for r in cleanup) else 2


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--seed',required=True);parser.add_argument('--seconds',type=int,default=1200)
    args=parser.parse_args();raise SystemExit(run(args.output,args.seed,seconds=args.seconds))
