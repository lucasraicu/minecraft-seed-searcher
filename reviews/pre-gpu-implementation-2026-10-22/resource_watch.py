"""Observe only this task's named benchmark trees and private output bounds."""
from pathlib import Path
import subprocess,json,time,os,signal
R=Path(__file__).resolve().parents[2];E=Path(__file__).parent;B=Path.home()/'.local/share/antigravity-worker-mcp/pre-gpu-readiness-approved-20261022'
old=json.loads((E/'RESOURCE_WATCH.json').read_text());peak=old['peak_owned_rss_bytes'];disk_peak=old['private_logical_disk_peak_bytes'];samples=old['samples'];started=old['started']
while not(E/'STOP_RESOURCE_WATCH_2').exists():
 rows=[]
 for line in subprocess.check_output(['ps','-axo','pid=,ppid=,rss=,command='],text=True).splitlines():
  x=line.strip().split(None,3)
  if len(x)==4:rows.append((int(x[0]),int(x[1]),int(x[2])*1024,x[3]))
 roots={pid for pid,ppid,rss,cmd in rows if ('python' in cmd.lower()and (str(E)+'/'in cmd or 'reviews/pre-gpu-implementation-2026-10-22/'in cmd or str(B)+'/'in cmd))and 'resource_watch.py'not in cmd}
 selected=set(roots)
 for _ in range(8):selected|={pid for pid,ppid,_,_ in rows if ppid in selected}
 total=sum(rss for pid,_,rss,_ in rows if pid in selected);peak=max(peak,total)
 disk=sum(p.stat().st_size for p in B.rglob('*')if p.is_file());disk_peak=max(disk_peak,disk);samples+=1
 status='PASS'if total<=4<<30 and disk<=3<<30 else'EXCEEDED'
 (E/'RESOURCE_WATCH.json').write_text(json.dumps(dict(status=status,started=started,samples=samples,peak_owned_rss_bytes=peak,private_logical_disk_peak_bytes=disk_peak,private_disk_cap_bytes=3<<30,aggregate_rss_cap_bytes=4<<30,current_owned_pids=sorted(selected),scope='Named private benchmark trees; source/worker/test snapshot extra disk accounted separately in final ledger'),indent=2)+'\n')
 if status=='EXCEEDED':
  for pid in sorted(selected,reverse=True):
   if pid not in (os.getpid(),91321,22035,17880):
    try:os.kill(pid,signal.SIGTERM)
    except ProcessLookupError:pass
  raise SystemExit('Owned resource cap exceeded')
 time.sleep(1)
