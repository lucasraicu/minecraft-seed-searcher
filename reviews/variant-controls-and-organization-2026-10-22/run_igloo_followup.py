"""Resume only owned worlds, preserve initial evidence, never reset resource spend."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import time
from run_variant_controls import HERE,OUTPUT,LIMIT,write,size,run

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--execute-case',type=int,choices=(0,3,4));a=parser.parse_args()
    raw=(HERE/'IGLOO_FOLLOWUP_PROTOCOL.json').read_bytes();protocol=json.loads(raw)
    if a.execute_case is None:print(json.dumps(dict(dry_run=True,cases=[c['case']['id']for c in protocol['cases']])));return
    selected=next(c for c in protocol['cases']if c['case']['id']==a.execute_case);case=selected['case']
    if a.execute_case in(3,4):
        approval=json.loads((HERE/'IGLOO_REQUEST_AMENDMENT_APPROVAL.json').read_text())
        if approval['approval']!='Approve the two additional 59-block requests':raise ValueError('Exact request amendment missing')
        if len(selected['requests'])!=1 or len(selected['requests'][0]['points'])!=59:raise ValueError('Amended request bounds')
    old_directory=OUTPUT/f'case-{case["id"]}';old_report=(old_directory/'report.json').read_bytes()
    if hashlib.sha256(old_report).hexdigest()!=selected['prior_report_sha256']:raise ValueError('Initial report drift')
    budget_path=OUTPUT/'BDS_BUDGET.json';budget=json.loads(budget_path.read_text())
    if budget['active']is not None or case['id']in budget.get('followup_attempted',[]):raise ValueError('Active/already attempted followup')
    prior=selected['prior_seconds'];wall=min(int(180-prior),int(1200-budget['charged_seconds']))
    if wall<30 or size()>LIMIT-(128<<20):raise ValueError('Remaining per-world/global/output allowance')
    if len(selected['requests'])+selected['prior_requests']>(9 if case['id']in(3,4)else 8):raise ValueError('Cumulative requests')
    work=old_directory/'worlds/world';world=work/'worlds/spawn_audit'
    # No running container may own this exact world/work mount.
    ids=subprocess.check_output(['docker','ps','-q'],text=True).split()
    for cid in ids:
        info=json.loads(subprocess.check_output(['docker','inspect',cid],text=True))[0]
        if any(Path(m.get('Source','/invalid'))==work for m in info.get('Mounts',[])):raise ValueError('World still has an active writer')
    hashes={str(p.relative_to(world)):hashlib.sha256(p.read_bytes()).hexdigest()for p in world.rglob('*')if p.is_file()}
    archive=OUTPUT/f'case-{case["id"]}-before-followup.tar.gz'
    if archive.exists():raise FileExistsError(archive)
    with tarfile.open(archive,'w:gz')as tar:tar.add(world,arcname='world')
    with tempfile.TemporaryDirectory(dir=OUTPUT)as tmp:
        with tarfile.open(archive)as tar:tar.extractall(tmp,filter='data')
        extracted=Path(tmp)/'world'
        if hashes!={str(p.relative_to(extracted)):hashlib.sha256(p.read_bytes()).hexdigest()for p in extracted.rglob('*')if p.is_file()}:raise ValueError('Pre-resume archive differs')
    provenance=dict(original_case=case['id'],original_report_sha256=selected['prior_report_sha256'],archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),archive=str(archive),original_world_hashes=hashes,prior_seconds=prior,prior_requests=selected['prior_requests'],reason='Separate observer-geometry followup; earlier failure/UNKNOWN remains retained')
    budget.setdefault('followup_attempted',[]).append(case['id']);budget['charged_seconds']+=wall;budget['active']=dict(followup_case=case['id'],reserved_seconds=wall,started_unix=time.time());write(budget_path,budget)
    report=run(case,wall,hashlib.sha256(raw).hexdigest(),followup=dict(work=str(work),requests=selected['requests'],provenance=provenance))
    report['cumulative_world_seconds']=prior+report['wall_seconds'];report['cumulative_world_requests']=selected['prior_requests']+len(report['results'])
    if report['cumulative_world_seconds']>180 or report['cumulative_world_requests']>(9 if case['id']in(3,4)else 8):report['status']='failed'
    write(OUTPUT/f'followup-case-{case["id"]}/report.json',report)
    budget['charged_seconds']+=report['wall_seconds']-wall;budget['active']=None;budget['output_bytes']=size();budget.setdefault('followups',[]).append(dict(case=case['id'],seconds=report['wall_seconds'],cumulative_world_seconds=report['cumulative_world_seconds'],cumulative_world_requests=report['cumulative_world_requests'],status=report['status']));write(budget_path,budget)
    print(json.dumps(dict(case=case['id'],status=report['status'],seconds=report['wall_seconds'],world_seconds=report['cumulative_world_seconds'],world_requests=report['cumulative_world_requests'],total_seconds=budget['charged_seconds'],error=report.get('error'))))

if __name__=='__main__':main()
