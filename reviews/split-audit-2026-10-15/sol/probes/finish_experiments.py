"""Run only after confirmation-main exits. All heavy operations are sequential."""
from pathlib import Path
import subprocess
import sys
from experiment import ROOT, WORK
import argparse
import os
import time

parser=argparse.ArgumentParser()
parser.add_argument('--wait-pid',type=int)
args=parser.parse_args()
if args.wait_pid:
    while True:
        try:os.kill(args.wait_pid,0)
        except ProcessLookupError:break
        time.sleep(0.5)

probe=ROOT/'reviews/split-audit-2026-10-15/sol/probes'
def call(script,*args):
    print(script,*args,flush=True)
    with (WORK/(script+'-'+(args[-1] if args else 'run')+'.log')).open('w') as stream:
        subprocess.run([sys.executable,str(probe/script),*args],stdout=stream,stderr=subprocess.STDOUT,check=True)

call('parity.py','--allow-heavy','--arms','lazy-no-surface-init','dark-gate','--component-count','256')
call('experiment.py','bench','--allow-heavy','--arms','lazy-no-surface-init','dark-gate',
     '--count','200000','--start','75000000','--trials','3','--output','screen-dark-gate.json')
call('scheduling.py','--allow-heavy')
call('scheduling.py','--allow-heavy','--confirm')
call('experiment.py','bench','--allow-heavy','--arms','control','lazy','no-surface-init','lazy-no-surface-init',
     '--count','300000','--start','90000000','--trials','2','--output','codex-performance-recheck.json')
call('prepare_survivor.py')
call('experiment.py','build-diag','--allow-heavy')
call('survivor.py','--allow-heavy')
call('experiment.py','bench','--allow-heavy','--arms','lazy-no-surface-init','dark-gate',
     '--count','1500000','--start','100000000','--trials','5','--output','confirm-dark-gate.json')
call('remaining_profile.py')
call('profile.py','--allow-heavy','--count','100000','--start','50000000','--threads','34',
     '--build',str(WORK/'diagnostic-optimized/native-build'),'--output','profile-optimized.json')
with (WORK/'targeted-tests.log').open('w') as stream:
    subprocess.run([sys.executable,'-m','pytest','tests/test_dynamic_baseline.py',
                    'tests/test_dynamic_integration.py','-q','-k','not web_bds_job'],
                   stdout=stream,stderr=subprocess.STDOUT,check=True)
print('SEQUENTIAL EXPERIMENTS COMPLETE',flush=True)
