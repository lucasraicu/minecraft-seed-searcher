"""One pinned disposable-world preflight, not candidate eligibility proof."""
import hashlib
import json
from pathlib import Path
import signal
import subprocess
import time

from seed_search.realm.cli import load
from seed_search.realm.runner import _seed
from seed_search.realm.verification import VerificationAdapter, tooling_identity, saved_blocks_consistent

ROOT=Path(__file__).resolve().parent
cfg=load('config/realm.yaml')
seed=str(_seed(2028375,cfg['search']))
cfg['bds'].update(verification_budget=1,persist_snapshot=True,
                  evidence_dir=str(ROOT/'bds-evidence'))
adapter=VerificationAdapter(cfg)
def timeout(signum,frame):
    raise TimeoutError('Bounded BDS preflight exceeded 180 seconds')
signal.signal(signal.SIGALRM,timeout)
before=time.monotonic()
signal.alarm(180)
observation=adapter.verify(seed,(-16,-16,16,16),spacing=8,selection_reason='explicit')
signal.alarm(0)
cached=adapter.verify(seed,(-16,-16,16,16),spacing=8,selection_reason='explicit')
containers=subprocess.run(['docker','ps','--format','{{.Names}}'],capture_output=True,text=True,timeout=15,check=True)
raw=observation.get('evidence',{})
raster=observation.get('raster',{})
preflight_pass=(adapter.used==1 and cached==observation
    and sum(map(sum,raster.get('known',[])))==16
    and raw.get('stable') is True and raw.get('complete_snapshot') is True
    and raw.get('cleanup',{}).get('clean_shutdown') is True
    and saved_blocks_consistent(raw.get('saved_blocks',{}))
    and not containers.stdout.strip())
summary={
    'scope':'32-square origin actual-block observation on known predictor survivor; not full world eligibility',
    'index':2028375,'seed':seed,'wall_seconds':time.monotonic()-before,
    'attempts_used':adapter.used,'cached_observation_equal':cached==observation,
    'config_sha256':hashlib.sha256(Path('config/realm.yaml').read_bytes()).hexdigest(),
    'current_tools_sha256':tooling_identity(),'runtime_identity':adapter.identity,
    'status':observation.get('status'),'preflight_pass':preflight_pass,
    'running_containers_after':containers.stdout.splitlines(),
    'limitations':[
        'No Bedrock client is available: initial-player placement cannot be captured here.',
        'Stable Script API does not enumerate complete structures; no structure recall or full count certification.',
        'Observed support blocks do not prove natural-ground provenance.',
        'A 32-square sample does not establish full terrain, marine structures, or safe travel routes.'
    ],'observation':observation}
(ROOT/'bds-preflight.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:summary[k] for k in ('status','seed','attempts_used','cached_observation_equal','wall_seconds','running_containers_after')}))
if not preflight_pass:
    raise SystemExit(1)
