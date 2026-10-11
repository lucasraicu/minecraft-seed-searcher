"""Isolated BDS console controller; does not import or modify the seed finder."""
from pathlib import Path
import subprocess, os, time, json, re, threading, queue
ROOT=Path(__file__).resolve().parent
DOCKER='/Applications/Docker.app/Contents/Resources/bin/docker'
ENV=dict(os.environ)
ENV['PATH']=str(Path(DOCKER).parent)+os.pathsep+ENV.get('PATH','')
def docker(*args, **kwargs):
    kwargs.setdefault('timeout',60)
    return subprocess.run([DOCKER,*args],env=ENV,check=True,**kwargs)
class Console:
    def __init__(self,name,label):
        self.name=name; self.lines=[];self.events=queue.Queue()
        self.log=open(ROOT/f'{label}.log','w',buffering=1)
        try:
            docker('start',name,capture_output=True,text=True)
            started=docker('inspect',name,'--format','{{.State.StartedAt}}',capture_output=True,text=True).stdout.strip()
            self.process=subprocess.Popen([DOCKER,'logs','--follow','--since',started,name],env=ENV,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
            self.thread=threading.Thread(target=self.read,daemon=True);self.thread.start()
        except BaseException:
            self.close_io()
            raise
    def read(self):
        for line in self.process.stdout:
            self.lines.append(line);self.log.write(line);self.events.put(line)
    def command(self,cmd,timeout=10):
        self.log.write('CONSOLE_INPUT '+cmd+'\n')
        docker('exec',self.name,'/bin/sh','-c','printf "%s\\n" "$1" > /srv/bds/poc-console','sh',cmd,capture_output=True,text=True,timeout=timeout)
    def wait_for(self,text,timeout=45):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            try:line=self.events.get(timeout=min(1,max(.01,end-time.monotonic())))
            except queue.Empty:
                if self.process.poll() is not None:raise RuntimeError(f'Server exited {self.process.returncode}')
                continue
            if text in line:return line
        raise TimeoutError(f'Timed out waiting for {text}')
    def stop(self):
        self.command('stop',timeout=5)
        self.process.wait(timeout=20)
        state=container_state(self.name)
        if not state.get('stopped'):
            raise RuntimeError('Docker did not confirm stopped BDS container')
        return state['exit_code']
    def close_io(self):
        errors=[]
        process=getattr(self,'process',None)
        if process is not None:
            try:
                if process.poll() is None:
                    process.terminate()
                    try:process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        process.kill();process.wait(timeout=3)
            except BaseException as error:errors.append(type(error).__name__+': '+str(error))
        thread=getattr(self,'thread',None)
        if thread is not None:
            try:thread.join(timeout=2)
            except BaseException as error:errors.append(type(error).__name__+': '+str(error))
        log=getattr(self,'log',None)
        if log is not None and not log.closed:
            try:
                if thread is None or not thread.is_alive():log.close()
                else:errors.append('Log reader did not stop; log remains open')
            except BaseException as error:errors.append(type(error).__name__+': '+str(error))
        return errors


def container_state(name):
    """Only successful Docker state/list queries establish stopped or absent."""
    errors=[];interrupted=False
    try:
        value=json.loads(docker('inspect',name,capture_output=True,text=True,timeout=5).stdout)[0]['State']
        if not isinstance(value['Running'],bool) or isinstance(value['ExitCode'],bool) or not isinstance(value['ExitCode'],int):
            raise ValueError('Malformed Docker container state')
        return {'exists':True,'running':value['Running'],'stopped':not value['Running'],'exit_code':value['ExitCode']}
    except BaseException as error:
        errors.append(type(error).__name__+': '+str(error));interrupted|=isinstance(error,KeyboardInterrupt)
    try:
        names=docker('ps','-a','--format','{{.Names}}',capture_output=True,text=True,timeout=5).stdout.splitlines()
        if name not in names:return {'exists':False,'removed':True,'stopped':False,'errors':errors,'interrupted':interrupted}
    except BaseException as error:
        errors.append(type(error).__name__+': '+str(error));interrupted|=isinstance(error,KeyboardInterrupt)
    return {'exists':None,'running':None,'stopped':False,'errors':errors,'interrupted':interrupted}


def cleanup_container(name,console=None):
    """Bounded graceful stop, Docker stop, then force removal if still unsafe."""
    report={'actions':[],'graceful':False,'stopped':False,'removed':False,'interrupted':False}
    def action(label,fn):
        try:
            value=fn();report['actions'].append({'action':label,'ok':True});return value
        except BaseException as error:
            report['actions'].append({'action':label,'ok':False,'error_type':type(error).__name__,'error':str(error)})
            report['interrupted']|=isinstance(error,(KeyboardInterrupt,SystemExit))
            if isinstance(error,SystemExit):
                code=error.code if isinstance(error.code,(type(None),str,int,bool)) else str(error.code)
                report['termination']={'type':'SystemExit','code':code}
            return None
    if console is not None:
        code=action('console_stop',console.stop)
        report['graceful']=isinstance(code,int) and not isinstance(code,bool) and code==0
    state=container_state(name)
    report['interrupted']|=state.get('interrupted',False)
    report['graceful'] &= state.get('stopped',False) and state.get('exit_code')==0
    if not report['graceful'] or not state.get('stopped'):
        action('docker_stop',lambda:docker('stop','--time','10',name,capture_output=True,text=True,timeout=15))
        state=container_state(name)
        report['interrupted']|=state.get('interrupted',False)
    if not state.get('stopped') and not state.get('removed'):
        removed=action('docker_force_remove',lambda:docker('rm','--force',name,capture_output=True,text=True,timeout=15))
        state=container_state(name)
        report['interrupted']|=state.get('interrupted',False)
        if removed is not None:state={'exists':False,'removed':True,'stopped':False,'removal_command_succeeded':True}
    report.update({'state':state,'stopped':state.get('stopped',False),'removed':state.get('removed',False),
                   'exit_code':state.get('exit_code'),'clean_shutdown':report['graceful'] and state.get('stopped',False) and state.get('exit_code')==0})
    if console is not None and hasattr(console,'close_io'):
        errors=action('close_console_io',console.close_io)
        report['io_errors']=errors
    return report

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['initial','regions']);a=ap.parse_args()
    c=Console('bds-verification-poc',a.mode)
    print(c.wait_for('Server started.').strip(),flush=True)
    if a.mode=='initial':
        c.command('list');print(c.wait_for('players online').strip(),flush=True)
        time.sleep(3)
        c.command('testforblock 4096 64 -4096 stone')
        try:print(c.wait_for('Cannot',timeout=5).strip(),flush=True)
        except TimeoutError:pass
    else:
        ready=[line for line in c.lines if 'POC_READY' in line]
        if ready: print(ready[-1].strip(),flush=True)
        else: print(c.wait_for('POC_READY').strip(),flush=True)
        observations=[]
        tests=[{'id':'positive128','x0':8192,'z0':-8192,'side':128,'spacing':16},
               {'id':'negative256','x0':-8448,'z0':8448,'side':256,'spacing':16}]
        for q in tests:
            # 256 square = 256 chunks; split into four 64-chunk rectangles.
            start=time.monotonic()
            tile=min(q['side'],128)
            for dz in range(0,q['side'],tile):
                for dx in range(0,q['side'],tile):
                    x=q['x0']+dx;z=q['z0']+dz
                    c.command(f'tickingarea add {x} 0 {z} {x+tile-1} 0 {z+tile-1} {q["id"]}_{dx}_{dz} true')
            summary=None
            for attempt in range(1,11):
                time.sleep(2)
                c.command('scriptevent bds_poc:scan '+json.dumps(q,separators=(',',':')))
                line=c.wait_for('POC_DONE',timeout=60)
                summary=json.loads(line.split('POC_DONE ',1)[1])
                if summary['missing']==0:break
                print(f"{q['id']}: attempt {attempt}, {summary['missing']} missing; awaiting chunk readiness",flush=True)
            summary['requestToReadCompleteSeconds']=time.monotonic()-start
            summary['attempts']=attempt;summary['region']=q
            print(json.dumps(summary),flush=True);observations.append(summary)
            if summary['missing']:raise RuntimeError('Missing sampled chunks after bounded retries')
        columns=[]
        for line in c.lines:
            if 'POC_COLUMN ' in line:
                columns.append(json.loads(line.split('POC_COLUMN ',1)[1]))
        columns=list({(v['id'],v['x'],v['z']):v for v in columns}.values())
        (ROOT/'sampled-columns.json').write_text(json.dumps(columns,indent=2)+'\n')
        probes=[]
        for category in [lambda x:x['waterDepth']>0,lambda x:bool(x['discarded']),lambda x:x['x']%16==0]:
            for col in [v for v in columns if category(v)][:4]:
                for probe in col['probes']:
                    if probe not in probes:probes.append(probe)
        checks=[]
        for p in probes:
            c.command(f"testforblock {p['x']} {p['y']} {p['z']} {p['block']}")
            line=c.wait_for('Successfully found',timeout=5)
            # Preserve output for review; testforblock success has its own exact message.
            checks.append({'probe':p,'response':line.strip()})
        (ROOT/'direct-block-checks.json').write_text(json.dumps(checks,indent=2)+'\n')
        (ROOT/'region-generation-results.json').write_text(json.dumps(observations,indent=2)+'\n')
        resources=docker('exec','bds-verification-poc','/bin/sh','-c','cat /sys/fs/cgroup/memory.peak; cat /sys/fs/cgroup/cpu.stat',capture_output=True,text=True)
        (ROOT/'bds-cgroup-resources.txt').write_text(resources.stdout)
    code=c.stop();print('Clean shutdown process exit:',code,flush=True)
    assert code==0
