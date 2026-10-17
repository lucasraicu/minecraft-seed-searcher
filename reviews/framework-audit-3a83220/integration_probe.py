"""Small isolated integration reproductions; all writes stay in this audit dir."""
from pathlib import Path
import copy
import hashlib
import json
import sqlite3

from seed_search.realm.config import dynamic_v3_blueprint_config, validate_config
from seed_search.realm.native_batch import Prototype, run_native_scan
from seed_search.web import server

OUT=Path(__file__).resolve().parent
REPO=OUT.parents[1]
result={}
cfg=dynamic_v3_blueprint_config()
result['default_search_top_k']=cfg['search'].get('top_k',0)
old=copy.deepcopy(cfg)
old['search']['centroid_weights'].update(village=3,trial_chamber=2,stronghold=1)
try:
    validate_config(old)
except ValueError as error:
    result['old_v3_config_validation_error']=str(error)
result['old_and_new_screening_revision']=cfg['screening_revision']
for name,path in [('web_default',server.DEFAULT_NATIVE_BUILD),('current',REPO/'runs/dynamic-baseline-2048/native')]:
    identity=json.loads((path/'identity.json').read_text())
    changed=[name for name,sha in identity['inputs'].items() if hashlib.sha256((REPO/name).read_bytes()).hexdigest()!=sha]
    arm={'path':str(path),'source_mismatches':changed}
    try:
        prototype=Prototype(path,cfg)
        arm['init']='accepted'
        with prototype.sweep([456],fixtures=[(0,0,-1)]) as batch:
            record=batch.records()[0]
            arm['fixture_score']=record['anchors'][0]['baseline_score_observed']
    except Exception as error:
        arm['error']=f'{type(error).__name__}: {error}'
    result[name]=arm
cfg['biomes']['required_families']=[]
cfg['search'].update(sequence='manifest',manifest_seeds=['-3336796033057908633'])
run=OUT/'topk-default-off-run'
if (run/'realm.sqlite').exists():
    raise SystemExit('Choose a fresh output path for repeated integration reproduction')
status=run_native_scan(cfg,run,count=1,native_build=REPO/'runs/dynamic-baseline-2048/native',native_threads=1,native_batch_size=1,retention='survivors')
with sqlite3.connect(run/'realm.sqlite') as db:
    result['default_scan']={'completed_seeds':status['completed_seeds'],'candidate_count':db.execute('SELECT count(*) FROM candidates').fetchone()[0], 'top50_json_exists':(run/'top50.json').exists(),'top_candidates_table_exists':db.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='top_candidates'").fetchone()[0]}
(OUT/'integration_probe.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
