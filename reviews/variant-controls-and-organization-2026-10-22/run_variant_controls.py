"""Explicit approved, durably charged disposable BDS controls. No seed searches."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import queue
import shutil
import subprocess
import threading
import time
import uuid

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUTPUT=Path('/Users/lucasraicu/.local/share/antigravity-worker-mcp/variant-controls-approved-20261022')
IMAGE='sha256:cf479afd0ab8a8bb095f7aa71fd42064cf5ba7aff6c8a8f4f5503aac826511d8'
LIMIT=2<<30

def write(path,value):
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(path)

def size():
    return sum(p.stat().st_size for p in OUTPUT.rglob('*')if not p.is_symlink() and p.is_file())

def requests(case):
    x,z=case['start'];out=[]
    for i in range(8):
        if case['dimension']=='overworld':
            v=[x-8,0,z-8+3*i,x+16,112,z-5+3*i]
            chunks=[[cx,cz]for cx in range(v[0]//16,(v[3]-1)//16+1)for cz in range(v[2]//16,(v[5]-1)//16+1)]
        else:
            v=None;chunks=[[x//16-4+i,z//16-4+j]for j in range(8)]
        out.append(dict(id=i,dimension=case['dimension'],chunks=chunks,volume=v))
    return out

def run(case,wall,protocol_sha,*,followup=None):
    directory=OUTPUT/(('followup-case-'if followup else'case-')+str(case['id']));directory.mkdir(exist_ok=False)
    spec=importlib.util.spec_from_file_location('saved_bds_setup',ROOT/'reviews/spawn-validation-2026-10-17/bds_runner.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);mod.BASE=directory
    shutil.copyfile(HERE/('igloo_followup_observer.js'if followup else'variant_observer.js'),directory/'observer.js')
    if followup:
        work=Path(followup['work'])
        shutil.copyfile(directory/'observer.js',work/'behavior_packs/spawn_observer/scripts/main.js')
    else:work=mod.prepare(case['seed'],'world')
    name='codex-variant-'+uuid.uuid4().hex[:12]
    settings=(work/'server.properties').read_bytes()
    report=dict(case=case,status='starting',protocol_sha256=protocol_sha,image=IMAGE,api='2.10.0',container=name,
                settings_sha256=hashlib.sha256(settings).hexdigest(),observer_sha256=hashlib.sha256((directory/'observer.js').read_bytes()).hexdigest(),results=[])
    if followup:report['followup_provenance']=followup['provenance']
    script='''set -eu
for p in /opt/bds/*; do
 b=$(basename "$p"); case "$b" in worlds|server.properties|behavior_packs|config) continue;; esac
 [ -e "/audit/$b" ] || ln -s "$p" "/audit/$b"
done
for p in /opt/bds/behavior_packs/*; do
 [ -e "$p" ] || continue; b=$(basename "$p")
 [ -e "/audit/behavior_packs/$b" ] || ln -s "$p" "/audit/behavior_packs/$b"
done
if [ -d /opt/bds/config ] && [ ! -e /audit/config ]; then cp -a /opt/bds/config /audit/config; fi
cd /audit
export LD_LIBRARY_PATH=/opt/bds
exec /usr/bin/timeout --signal=TERM --kill-after=5 '''+str(max(1,int(wall)-10))+''' /opt/bds/bedrock_server'''
    args=['docker','run','--rm','-i','--pull=never','--name',name,'--label','seed-search.variant='+name,'--cpus','2','--memory','2g','--pids-limit','256','--ulimit','core=0','--network','bridge','--read-only','--tmpfs','/tmp:rw,size=64m','--log-opt','max-size=4m','--mount',f'type=bind,src={work},dst=/audit','--workdir','/audit','--entrypoint','/bin/sh',IMAGE,'-c',script]
    events=queue.Queue();log=(directory/'console.log').open('w',buffering=1);started=time.monotonic();deadline=started+wall-20
    process=None;reader=None
    def receive():
        for line in process.stdout:
            log.write(line);events.put(line)
    def command(value):
        if time.monotonic()>=deadline or size()>LIMIT:raise TimeoutError('Time/output cap')
        log.write('AUDIT_INPUT '+value+'\n');process.stdin.write(value+'\n');process.stdin.flush()
    def wait_for(token,seconds):
        until=min(deadline,time.monotonic()+seconds)
        while time.monotonic()<until:
            if size()>LIMIT:raise OSError('Output cap')
            try:line=events.get(timeout=.2)
            except queue.Empty:
                if process.poll()is not None:raise RuntimeError('BDS exited')
                continue
            if 'VARIANT_ERROR' in line or 'VARIANT_CLEANUP_ERROR' in line:raise RuntimeError(line.strip())
            if token(line):return line
        raise TimeoutError('BDS response timeout')
    try:
        process=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
        reader=threading.Thread(target=receive,daemon=True);reader.start()
        line=wait_for(lambda s:'VARIANT_IDENTITY 'in s,75)
        identity=json.loads(line.split('VARIANT_IDENTITY ',1)[1]);report['identity']=identity
        if str(identity['seed'])!=case['seed'] or identity['api']!='2.10.0' or identity['players']!=0:raise ValueError('Identity mismatch')
        x,z=case['start'];kind=('temple'if followup else'igloo')if case['feature']=='igloo_basement'else'bastion_remnant'
        command(f'execute in {case["dimension"]} positioned {x} 64 {z} run locate structure {kind} false')
        located=wait_for(lambda s:any(k in s for k in ['The nearest','Syntax error','No valid structure','Could not find','Unknown command']),15)
        report['locate']=located.strip()
        import re
        match=re.search(r'\bat(?: block)?\s*\(?\s*(-?\d+)\s*,\s*(?:-?\d+|\(y\?\))\s*,\s*(-?\d+)',located)
        report['pregeneration_locate_start']=list(map(int,match.groups()))if match else None
        for req in(followup['requests']if followup else requests(case)):
            command('scriptevent variant_audit:observe '+json.dumps(req,separators=(',',':')))
            line=wait_for(lambda s:'VARIANT_RESULT 'in s,25)
            result=json.loads(line.split('VARIANT_RESULT ',1)[1])
            if any(result[k]!=req[k]for k in ['id','dimension','chunks','volume'])or result['blockReads']>8192:raise ValueError('Observation binding/cap')
            if followup and req.get('points'):
                if result['blockReads']>59 or [[v['x'],v['y'],v['z']]for v in result['pointRows']]!=req['points']:raise ValueError('Followup frozen point binding/cap')
            report['results'].append(result);write(directory/'report.json',report)
        command(f'execute in {case["dimension"]} positioned {x} 64 {z} run locate structure {kind} false')
        located=wait_for(lambda s:any(k in s for k in ['The nearest','Syntax error','No valid structure','Could not find','Unknown command']),15)
        report['postgeneration_locate']=located.strip()
        match=re.search(r'\bat(?: block)?\s*\(?\s*(-?\d+)\s*,\s*(?:-?\d+|\(y\?\))\s*,\s*(-?\d+)',located)
        report['actual_start']=list(map(int,match.groups()))if match else None
        report['locate_matches_frozen_start']=bool(match and max(abs(int(match[1])-x),abs(int(match[2])-z))<=16)
        command('save hold');saved=False
        for _ in range(6):
            command('save query')
            try:wait_for(lambda s:'Files are now ready'in s,1.5);saved=True;break
            except TimeoutError:pass
        command('save resume');report['save_confirmed']=saved
        if not saved:raise RuntimeError('No save acknowledgment')
        report['status']='observed'
    except Exception as error:
        report['status']='failed';report['error']=type(error).__name__+': '+str(error)
    finally:
        if process is not None and process.poll()is None:
            try:process.stdin.write('stop\n');process.stdin.flush();process.wait(timeout=5)
            except (OSError,subprocess.TimeoutExpired):pass
        report['clean_shutdown']=process is not None and process.poll()==0
        info=subprocess.run(['docker','inspect',name],capture_output=True,text=True,timeout=2)
        if info.returncode==0:
            data=json.loads(info.stdout)[0]
            if data['Config'].get('Labels',{}).get('seed-search.variant')!=name:raise RuntimeError('Cleanup identity mismatch')
            subprocess.run(['docker','rm','--force',name],capture_output=True,check=True,timeout=3)
        report['owned_container_removed']=subprocess.run(['docker','inspect',name],capture_output=True,timeout=2).returncode!=0
        if process is not None:
            try:process.wait(timeout=1)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=1)
        if reader:reader.join(timeout=1)
        log.close();report['wall_seconds']=time.monotonic()-started
        text=(directory/'console.log').read_text()
        report['build_verified']='Version: 1.26.52.3'in text
        if not report['build_verified']or not report['clean_shutdown']or not report['owned_container_removed']:report['status']='failed'
        write(directory/'report.json',report)
    return report

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--execute-case',type=int);a=parser.parse_args()
    raw=(HERE/'FROZEN_PROTOCOL.json').read_bytes();protocol=json.loads(raw);sha=hashlib.sha256(raw).hexdigest()
    for case in protocol['cases']:
        reqs=requests(case);assert len(reqs)==8
        for q in reqs:
            assert len(q['chunks'])<=10
            if q['volume']:
                x,y,z,X,Y,Z=q['volume'];assert(X-x)*(Y-y)*(Z-z)+len(q['chunks'])<=8192
    if a.execute_case is None:print(json.dumps(dict(dry_run=True,protocol_sha256=sha,worlds=len(protocol['cases']))));return
    ledger_path=OUTPUT/'BDS_BUDGET.json'
    ledger=json.loads(ledger_path.read_text())if ledger_path.exists()else dict(protocol_sha256=sha,charged_seconds=0,attempted=[],active=None)
    if ledger['protocol_sha256']!=sha or ledger['active']is not None or a.execute_case in ledger['attempted']:raise ValueError('Budget identity/active/attempted conflict')
    wall=min(180,1200-ledger['charged_seconds'])
    if wall<30 or size()>LIMIT-(64<<20):raise ValueError('Insufficient time/output budget')
    if subprocess.check_output(['docker','image','inspect',IMAGE,'--format','{{.Id}}'],text=True).strip()!=IMAGE:raise ValueError('Pinned image missing')
    case=next(c for c in protocol['cases']if c['id']==a.execute_case)
    ledger['charged_seconds']+=wall;ledger['attempted'].append(a.execute_case);ledger['active']=dict(case=a.execute_case,reserved_seconds=wall,started_unix=time.time());write(ledger_path,ledger)
    report=run(case,wall,sha)
    # On interruption the full reservation remains charged; no automatic rerun.
    ledger['charged_seconds']+=max(0,report['wall_seconds'])-wall;ledger['active']=None;ledger['output_bytes']=size();write(ledger_path,ledger)
    print(json.dumps(dict(case=a.execute_case,status=report['status'],error=report.get('error'),seconds=report['wall_seconds'],charged=ledger['charged_seconds'],bytes=ledger['output_bytes'])))

if __name__=='__main__':main()
