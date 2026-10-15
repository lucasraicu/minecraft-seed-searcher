import subprocess,sys,json,time
from pathlib import Path
out=Path('reviews/split-audit-2026-10-15/sol');out.mkdir(exist_ok=True)
p=subprocess.Popen([sys.executable,'/tmp/minecraft-sol-audit-20261015/sample_workload.py'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
try:
 r=subprocess.run(['/usr/bin/sample',str(p.pid),'4','5','-file',str(out/'mansion-sample.txt')],capture_output=True,text=True,timeout=15)
 meta={'pid':p.pid,'sample_returncode':r.returncode,'sample_stdout':r.stdout,'sample_stderr':r.stderr}
 try:
  r=subprocess.run(['xcrun','xctrace','record','--template','CPU Counters','--attach',str(p.pid),'--time-limit','3s','--output','/tmp/minecraft-sol-audit-20261015/counters.trace'],capture_output=True,text=True,timeout=15)
  meta.update(counters_returncode=r.returncode,counters_stdout=r.stdout,counters_stderr=r.stderr)
 except subprocess.TimeoutExpired as e:meta['counters_error']=str(e)
 (out/'sampling-metadata.json').write_text(json.dumps(meta,indent=2)+'\n')
finally:
 try:stdout,stderr=p.communicate(timeout=55)
 except subprocess.TimeoutExpired:p.terminate();stdout,stderr=p.communicate(timeout=5)
 print('sample target',p.returncode,stdout,stderr)
