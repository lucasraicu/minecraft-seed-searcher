#!/usr/bin/env python3
"""Run the frozen eight-world spawn pilot in newly owned, bounded BDS worlds."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import threading
import time
import types
import uuid

ROOT=Path(__file__).resolve().parents[1]
DOCKER='/Users/lucasraicu/.docker/bin/docker'
IMAGE='bedrock-verification-poc:1.26.52.3'
IMAGE_ID='sha256:cf479afd0ab8a8bb095f7aa71fd42064cf5ba7aff6c8a8f4f5503aac826511d8'


def run(output,protocol_path,estimator):
    protocol_bytes=protocol_path.read_bytes();protocol=json.loads(protocol_bytes)
    claimed=protocol.pop('protocol_sha256')
    assert hashlib.sha256(json.dumps(protocol,sort_keys=True,separators=(',',':')).encode()).hexdigest()==claimed
    seeds=protocol['seeds'];assert len(seeds)==len(set(seeds))==8
    assert protocol['allowance']==dict(worlds=8,concurrency=1,cpus=2,memory_gib=2,
        seconds_per_world=300,total_seconds=1200,owned_output_gib=1)
    output=output.absolute();output.mkdir(parents=True,exist_ok=False)
    (output/'frozen-protocol.json').write_bytes(protocol_bytes)
    estimate=subprocess.run([str(estimator.absolute())],input=''.join(s+'\n' for s in seeds),
        text=True,capture_output=True,check=True,timeout=15)
    predictions=[json.loads(s) for s in estimate.stdout.splitlines()]
    assert [r['seed'] for r in predictions]==seeds
    assert all(r['estimate']==r['repeat_estimate'] for r in predictions)
    (output/'predictions.json').write_text(json.dumps(predictions,indent=2)+'\n')
    shutil.copyfile(ROOT/'reviews/spawn-validation-2026-10-17/observer.js',output/'observer.js')
    spec=importlib.util.spec_from_file_location('spawn_audit_runner',ROOT/'reviews/spawn-validation-2026-10-17/bds_runner.py')
    runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
    runner.BASE=output;runner.DOCKER=DOCKER
    token=uuid.uuid4().hex[:12];label='seed-search.spawn-correction='+token
    started=time.monotonic();done=threading.Event();owned=set();results=[]
    def command(*args,timeout=30,check=True):
        return subprocess.run([DOCKER,*args],capture_output=True,text=True,check=check,timeout=timeout)
    assert command('image','inspect',IMAGE,'--format','{{.Id}}').stdout.strip()==IMAGE_ID
    command('run','--rm','--network','none','--cpus','1','--memory','128m','--label',label,
            '--read-only','--entrypoint','/usr/bin/timeout',IMAGE,'--version')
    def launch(args,**kwargs):
        args=list(args);assert args[:2]==[DOCKER,'run']
        name=args[args.index('--name')+1]
        assert command('inspect',name,check=False).returncode!=0
        assert args[args.index('--cpus')+1]=='2'
        args[args.index('--memory')+1]='2g'
        port=args.index('-p');del args[port:port+2]
        args[args.index('--entrypoint')+1]='/usr/bin/timeout'
        image=args.index(IMAGE)
        args[image+1:image+1]=['--signal=TERM','--kill-after=10','280','/bin/sh']
        args[2:2]=['--network','none','--label',label,'--read-only','--tmpfs','/tmp:rw,size=64m',
                   '--log-driver','json-file','--log-opt','max-size=5m','--log-opt','max-file=2']
        assert args[args.index('--memory')+1]=='2g' and '-p' not in args
        owned.add(name)
        process=subprocess.Popen(args,**kwargs)
        for _ in range(100):
            observed=command('inspect',name,check=False)
            if observed.returncode==0:
                inspected=json.loads(observed.stdout)[0]
                break
            if process.poll() is not None:raise RuntimeError('BDS container exited during creation')
            time.sleep(.05)
        else:raise TimeoutError('BDS container creation acknowledgement')
        host=inspected['HostConfig']
        assert host['NanoCpus']==2_000_000_000 and host['Memory']==2<<30
        assert inspected['Config']['Labels']['seed-search.spawn-correction']==token
        return process
    runner.subprocess=types.SimpleNamespace(Popen=launch,run=subprocess.run,
        PIPE=subprocess.PIPE,STDOUT=subprocess.STDOUT,TimeoutExpired=subprocess.TimeoutExpired)
    def interrupted(*_):raise TimeoutError('Spawn pilot wall/output allowance exhausted')
    previous=signal.signal(signal.SIGALRM,interrupted);signal.alarm(1200)
    def monitor():
        while not done.wait(.5):
            try:
                size=sum(p.stat().st_size for p in output.rglob('*') if p.is_file() and not p.is_symlink())
                if size>1<<30:os.kill(os.getpid(),signal.SIGALRM);return
            except FileNotFoundError:pass
    watcher=threading.Thread(target=monitor,daemon=True);watcher.start()
    error=None
    try:
        for i,pred in enumerate(predictions):
            world=None;begin=time.monotonic();row=dict(seed=pred['seed'],status='failed')
            try:
                world=runner.RunningWorld(pred['seed'],token+'-'+str(i))
                world.wait('world_tick40',timeout=65)
                row['observations']=world.rows.copy()
            finally:
                row['clean_shutdown']=world.stop() if world else False
            if not row['clean_shutdown']:raise RuntimeError('World did not save/shutdown cleanly')
            data=(world.work/'worlds/spawn_audit/level.dat').read_bytes()
            (output/f'level-{i}.dat').write_bytes(data)
            code="import json,pathlib,amulet_nbt; d=amulet_nbt.load(pathlib.Path('/input/level.dat').read_bytes()[8:],compressed=False,little_endian=True).compound; print(json.dumps(dict(seed=str(d['RandomSeed']),spawn={k:int(d['Spawn'+k.upper()]) for k in ('x','y','z')})))"
            saved=json.loads(command('run','--rm','--network','none','--cpus','1','--memory','256m',
                '--label',label,'--read-only','--mount',f'type=bind,src={world.work}/worlds/spawn_audit,dst=/input,readonly',
                '--entrypoint','/opt/reader/bin/python',IMAGE,'-c',code).stdout)
            assert saved['seed']==pred['seed']
            assert {r['phase'] for r in row['observations']}=={'world_load','world_tick20','world_tick40'}
            for observation in row['observations']:
                assert observation['seed']==pred['seed'] and observation['players']==0 and observation['spawnRadius']==10
                assert observation['defaultSpawn']==saved['spawn']
            actual=[saved['spawn']['x'],saved['spawn']['z']]
            row.update(status='match' if actual==pred['estimate'] else 'mismatch',saved=saved,
                predicted=pred['estimate'],level_dat_sha256=hashlib.sha256(data).hexdigest(),
                properties_sha256=hashlib.sha256((world.work/'server.properties').read_bytes()).hexdigest(),
                seconds=time.monotonic()-begin)
            assert row['seconds']<300
            results.append(row);(output/'results.json').write_text(json.dumps(results,indent=2)+'\n')
            print(json.dumps(dict(completed=len(results),seed=pred['seed'],status=row['status'],seconds=row['seconds'])),flush=True)
            if row['status']!='match':raise RuntimeError('Fresh spawn mismatch; adoption blocked')
    except Exception as exc:
        error=type(exc).__name__+': '+str(exc)
        raise
    finally:
        done.set();watcher.join(timeout=2);signal.alarm(0);signal.signal(signal.SIGALRM,previous)
        for name in sorted(owned):
            exists=command('inspect',name,check=False)
            if exists.returncode==0:
                record=json.loads(exists.stdout)[0]
                if record['Config']['Labels'].get('seed-search.spawn-correction')!=token:
                    raise RuntimeError('Cleanup ownership mismatch')
                command('rm','--force',name)
        leftovers=command('ps','--all','--filter','label='+label,'--format','{{.Names}}').stdout.strip()
        summary=dict(revision='fresh-spawn-controls-result-v1',protocol_sha256=claimed,
            estimator_sha256=hashlib.sha256(estimator.read_bytes()).hexdigest(),image_id=IMAGE_ID,
            completed=len(results),matches=sum(r['status']=='match' for r in results),
            error=error,owned_containers_removed=not leftovers,seconds=time.monotonic()-started)
        (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
        assert not leftovers
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--protocol',type=Path,required=True)
    parser.add_argument('--estimator',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(run(args.output,args.protocol,args.estimator),indent=2))
