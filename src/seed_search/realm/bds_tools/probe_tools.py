"""Standalone BDS diagnostics: no seed-finder imports or edits."""
from pathlib import Path
import sys,json,time,queue,hashlib,statistics
BASE=Path(__file__).resolve().parent
ROOT=Path(__file__).resolve().parent
from .poc_control import docker,Console,container_state
IMAGE='bedrock-verification-poc:1.26.52.3'
class FixtureRequestError(RuntimeError):
    def __init__(self,message,fixture_report=None):
        super().__init__(message)
        self.fixture_report=fixture_report

def create(name,seed,cpus=4):
    # Refuse to overwrite prior evidence or volumes on accidental reruns.
    docker('volume','create',name+'-data',capture_output=True,text=True)
    docker('run','--rm','--entrypoint','/bin/sh','--mount',f'type=volume,src={name}-data,dst=/srv/bds',IMAGE,'-c','test ! -e /srv/bds/bedrock_server && cp -a /opt/bds/. /srv/bds/',capture_output=True,text=True)
    docker('create','--name',name,'--cpus',str(cpus),'--memory','6g','--log-driver','local','--mount',f'type=volume,src={name}-data,dst=/srv/bds',IMAGE,capture_output=True,text=True)
    props=(BASE/'poc-server.properties').read_text().replace('level-seed=-1234567890123456789','level-seed='+str(seed)).replace('max-threads=4','max-threads='+str(cpus))
    path=ROOT/(name+'.properties');path.write_text(props)
    docker('cp',str(path),name+':/srv/bds/server.properties',capture_output=True,text=True)
    pack=ROOT/(name+'-pack');(pack/'scripts').mkdir(parents=True)
    (pack/'manifest.json').write_bytes((BASE/'manifest.json').read_bytes())
    for script in ('main.js','column_policy.js','fixture_policy.js'):
        (pack/'scripts'/script).write_bytes((BASE/script).read_bytes())
    docker('cp',str(pack),name+':/srv/bds/behavior_packs/poc_pack',capture_output=True,text=True)
    if (BASE/'manifest.json').exists():
        docker('cp',str(BASE/'manifest.json'),name+':/srv/bds/behavior_packs/poc_pack/manifest.json',capture_output=True,text=True)
    docker('cp',str(BASE/'main.js'),name+':/srv/bds/behavior_packs/poc_pack/scripts/main.js',capture_output=True,text=True)
    docker('run','--rm','--entrypoint','mkdir','--mount',f'type=volume,src={name}-data,dst=/srv/bds',IMAGE,'-p','/srv/bds/worlds/verification_poc',capture_output=True,text=True)
    docker('cp',str(BASE/'world_behavior_packs.json'),name+':/srv/bds/worlds/verification_poc/world_behavior_packs.json',capture_output=True,text=True)
    return name
class Probe(Console):
    def __init__(self,name,label):
        start=time.monotonic()
        try:
            super().__init__(name,label)
            self.wait_for('Server started.',timeout=60)
            self.wait_for('PROBE_READY',timeout=30)
        except BaseException:
            self.close_io()
            raise
        self.start_seconds=time.monotonic()-start
        print('START',name,round(self.start_seconds,3),flush=True)
    def request(self,action,q,timeout=180):
        marker={'load':'PROBE_LOADED','scan':'PROBE_DONE','dirty':'PROBE_DIRTY','unload':'PROBE_UNLOADED','check_sky':'PROBE_SKY','fixtures_create':'PROBE_FIXTURE_CREATED','fixtures_scan':'PROBE_FIXTURE_DONE','fixtures_restore':'PROBE_FIXTURE_RESTORED','biome_registry':'PROBE_BIOME_REGISTRY','permutations_resolve':'PROBE_PERMUTATIONS_RESOLVED'}[action]
        start=time.monotonic();self.command('scriptevent bds_probe:'+action+' '+json.dumps(q,separators=(',',':')))
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            try:line=self.events.get(timeout=1)
            except queue.Empty:
                if self.process.poll() is not None:raise RuntimeError('Server exited')
                continue
            if 'PROBE_FAILED ' in line:
                try:report=self.fixture_failure_report(q)
                except Exception as error:report={'status':'FAILED','diagnostic_reconstruction_error':str(error)}
                raise FixtureRequestError(line.strip(),report)
            if marker+' ' in line:
                payload=json.loads(line.split(marker+' ',1)[1])
                if payload['id']!=q['id']:raise RuntimeError('Unexpected result identifier')
                if action=='fixtures_create':
                    batches=[json.loads(value.split('PROBE_FIXTURE_JOURNAL ',1)[1]) for value in self.lines if 'PROBE_FIXTURE_JOURNAL ' in value]
                    selected=[batch for batch in batches if batch['id']==q['id']]
                    if [batch['batch'] for batch in selected]!=list(range(len(selected))):
                        raise RuntimeError('Incomplete fixture mutation journal batches')
                    payload['journal']['mutations']=[entry for batch in selected for entry in batch['mutations']]
                    if len(payload['journal']['mutations'])!=payload['journal']['expectedCells']:
                        raise RuntimeError('Incomplete fixture mutation journal')
                payload['wallSeconds']=time.monotonic()-start
                print(action,json.dumps(payload),flush=True)
                return payload
        raise TimeoutError(action+' '+q['id'])
    def rows(self,q):
        batches=[]
        for line in self.lines:
            if 'PROBE_BATCH ' in line:
                b=json.loads(line.split('PROBE_BATCH ',1)[1])
                if b['id']==q['id']:batches.append(b)
        assert [b['batch'] for b in batches]==list(range(len(batches)))
        rows=[row for batch in batches for row in batch['rows']]
        expected=((q['side']+q['spacing']-1)//q['spacing'])**2
        assert len(rows)==expected,(len(rows),expected)
        assert len({(r['x'],r['z']) for r in rows})==expected
        assert not any('error' in r for r in rows)
        return rows
    def fixture_failure_report(self,q):
        """Recover bounded setup/rollback artifacts already persisted in raw logs."""
        def payloads(marker):
            return [value for line in self.lines if marker+' ' in line
                    for value in [json.loads(line.split(marker+' ',1)[1])] if value['id']==q['id']]
        summaries=payloads('PROBE_FIXTURE_REPORT')
        if not summaries:return None
        report=summaries[-1]
        for marker,field,entry_key in (('PROBE_FIXTURE_JOURNAL','journal','mutations'),('PROBE_FIXTURE_ROLLBACK','restoration','results')):
            batches=payloads(marker)
            if [batch['batch'] for batch in batches]!=list(range(len(batches))):
                report['diagnostic_batches_complete']=False
            if report.get(field) is not None:
                report[field][entry_key]=[entry for batch in batches for entry in batch[entry_key]]
        if report.get('journal'):
            report['journal']['complete']=len(report['journal']['mutations'])==report['journal']['expectedCells']
        restoration=report.get('restoration')
        if restoration and restoration.get('results'):
            restoration['errors']=[entry for entry in restoration['results'] if entry.get('error')]
        return report
    def fixture_rows(self,q):
        batches=[json.loads(line.split('PROBE_FIXTURE_BATCH ',1)[1]) for line in self.lines if 'PROBE_FIXTURE_BATCH ' in line]
        selected=[batch for batch in batches if batch['id']==q['id']]
        if len(selected)!=1 or len(selected[0]['rows'])!=9:
            raise RuntimeError('Missing fixture columns')
        return selected[0]['rows']
    def restore_fixtures(self,q,journal):
        """Restore persisted original-air journal after restart, in small messages."""
        if (journal.get('policy')!='disposable-column-fixtures-v1' or not journal.get('mutations')
            or journal.get('expectedCells')!=len(journal['mutations'])
            or len({(p['x'],p['y'],p['z']) for p in journal['mutations']})!=len(journal['mutations'])):
            raise ValueError('Complete persisted fixture journal required')
        reports=[];request_errors=[];targets=list(reversed(journal['mutations']))
        for i in range(0,len(targets),6):
            # Only original identity/coordinate fields are needed for restoration.
            entries=[{key:p[key] for key in ('x','y','z','original')} for p in targets[i:i+6]]
            chunk={key:journal[key] for key in ('policy','x0','z0')};chunk['mutations']=list(reversed(entries))
            try:
                reports.append(self.request('fixtures_restore',{**q,'id':q['id']+'_restore_'+str(i//6),'journal':chunk}))
            except Exception as error:
                request_errors.append({'chunk':i//6,'error_type':type(error).__name__,'error':str(error)})
        restored=sum(report['restoredCells'] for report in reports)
        failures=[p for report in reports for p in report['errors']]
        return {'policy':journal['policy'],'status':'RESTORED' if not failures and not request_errors and restored==len(targets) else 'FAILED',
                'expectedCells':len(targets),'restoredCells':restored,'errors':failures,'requestErrors':request_errors,'chunks':reports}
    def save(self):
        start=time.monotonic();self.command('save hold')
        ready=False
        for _ in range(10):
            self.command('save query')
            try:self.wait_for('Files are now ready',timeout=2);ready=True;break
            except TimeoutError:pass
        self.command('save resume')
        if not ready:raise RuntimeError('Save confirmation did not arrive')
        return time.monotonic()-start
    def resources(self):
        text=docker('exec',self.name,'/bin/sh','-c','cat /sys/fs/cgroup/memory.peak; cat /sys/fs/cgroup/cpu.stat',capture_output=True,text=True).stdout
        return {'peakMemoryBytes':int(text.splitlines()[0]),'cpuStat':text.splitlines()[1:]}
def snapshot(name,label):
    state=container_state(name)
    if not state.get('stopped') or state.get('exit_code')!=0:
        raise RuntimeError('Snapshot requires authoritative clean stopped-container confirmation')
    folder=ROOT/label
    assert not folder.exists()
    docker('cp',name+':/srv/bds/worlds/verification_poc',str(folder),capture_output=True,text=True)
    return folder
def coverage(folder,regions):
    config=ROOT/(folder.name+'-regions.json');config.write_text(json.dumps(regions))
    start=time.monotonic()
    text=docker('run','--rm','--entrypoint','/opt/reader/bin/python','--mount',f'type=bind,src={ROOT},dst=/evidence,readonly','--mount',f'type=bind,src={BASE},dst=/tools,readonly',IMAGE,'/tools/snapshot_reader.py','/evidence/'+folder.name,'/evidence/'+config.name,capture_output=True,text=True).stdout
    report=json.loads(text);report['readerIncludingContainerSeconds']=time.monotonic()-start
    (ROOT/(folder.name+'-coverage.json')).write_text(json.dumps(report,indent=2)+'\n')
    return report
