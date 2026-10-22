"""Read-only analysis of one completed, bounded validation run; starts no jobs."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import statistics


def distribution(values):
    values=sorted(values)
    if not values:return None
    return dict(n=len(values),total=sum(values),mean=statistics.mean(values),median=statistics.median(values),
                p95=values[max(0,(95*len(values)+99)//100-1)],maximum=values[-1],minimum=values[0])


def analyze(root):
    def load(name):return json.loads((root/name).read_text())
    report=load('report.json');ledger=load('ingestion/ledger.json');controls=load('controls.json')
    features={};coverage={};structures=[]
    for receipt in ledger['receipts']:
        path=Path(receipt['checkpoint'])
        if not path.is_file():continue
        obs=json.loads(path.read_text())
        for fid,item in obs['metrics'].items():
            if 'wall_seconds' in item:
                features.setdefault(fid,{'wall_seconds':[],'cpu_seconds':[]})
                for unit in ('wall_seconds','cpu_seconds'):features[fid][unit].append(item[unit])
        for fid,item in obs['coverage'].items():
            counts=coverage.setdefault(fid,{})
            counts[item['status']]=counts.get(item['status'],0)+1
        structures.append(sum(len(points) for points in obs['structures'].values()))
    with sqlite3.connect((root/'catalog/catalog.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        numeric=db.execute('SELECT COUNT(*),SUM(length(payload_blob)) FROM layout').fetchone()
        compressed,uncompressed=db.execute('SELECT SUM(a.byte_length),SUM(a.uncompressed_length) FROM observation_set o JOIN artifact a ON a.sha256=o.manifest_sha256').fetchone()
        manifests=db.execute('SELECT COUNT(*),SUM(byte_length),SUM(uncompressed_length) FROM artifact').fetchone()
        pages=db.execute('PRAGMA page_count').fetchone()[0];page_size=db.execute('PRAGMA page_size').fetchone()[0]
    summaries={}
    for label in ('defaults','reduced_k1','reduced_k2','synthetic'):
        data=load(label+'-evaluation.json');groups={}
        for mode in ('origin','recommended'):
            rows=[r for r in data['rows'] if r['anchor_mode']==mode]
            groups[mode]=dict(reference_seconds=distribution([r['reference_seconds'] for r in rows]) if label=='defaults' else 'cached, excluded',
                retained_seconds=distribution([r['retained_seconds'] for r in rows]))
        summaries[label]={k:v for k,v in data.items() if k!='rows'}
        summaries[label]['query_timings_by_mode']=groups
    provenance={}
    for name in ('controls.json','heldout.json','ingestion/ledger.json','report.json','supervision.json','saved-verification.json','job-budget.json',
                 'defaults-evaluation.json','reduced_k1-evaluation.json','reduced_k2-evaluation.json','synthetic-evaluation.json'):
        provenance[name]=hashlib.sha256((root/name).read_bytes()).hexdigest()
    return dict(run_root=str(root),report={k:v for k,v in report.items() if k not in ('experiments','synthetic')},
        hardware=dict(cpu='Intel Xeon W-2191B @2.30GHz',physical_cores=18,logical_cpus=36,memory_bytes=68719476736,
            native_threads=1,background='Existing web server PID60144 kept running; no full pytest during timed run; start load averages2.05/2.68/2.54'),
        preflight=load('preflight.json')['summary'],supervision=load('supervision.json'),controls=controls,
        saved_verification=load('saved-verification.json'),cumulative_validation_budget=load('job-budget.json'),
        extraction=dict(receipt_wall_seconds=distribution([r['wall'] for r in ledger['receipts'] if r['attempts']]),
            receipt_cpu_seconds=distribution([r['cpu'] for r in ledger['receipts'] if r['cpu'] is not None]),
            native_feature_seconds={fid:{unit:distribution(values) for unit,values in units.items()} for fid,units in features.items()},
            feature_coverage=coverage,structure_points_per_world=distribution(structures)),
        storage=dict(layouts=numeric[0],packed_payload_bytes=numeric[1],observation_compressed_bytes=compressed,
            observation_json_bytes=uncompressed,all_artifacts_count=manifests[0],all_artifact_compressed_bytes=manifests[1],
            all_artifact_uncompressed_bytes=manifests[2],sqlite_bytes=pages*page_size,
            output_bytes=sum(p.stat().st_size for p in root.rglob('*') if p.is_file()),
            note='SQLite includes identifiers, metadata, indexes and364-byte payloads; output also includes checkpoints, selections, reports and validated backup'),
        experiments=summaries,raw_evidence_sha256=provenance,
        limits='100 declared predictor worlds, not production-capacity recall, true biome absence or generated-game accuracy')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('run_root',type=Path);args=parser.parse_args()
    print(json.dumps(analyze(args.run_root.resolve()),indent=2,sort_keys=True,allow_nan=False))
