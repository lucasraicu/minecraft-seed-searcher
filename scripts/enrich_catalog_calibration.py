#!/usr/bin/env python3
"""Bounded serial enrichment of an existing fixed seed cohort, never a personal sweep."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import sqlite3
import sys
import threading
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[key]='1'

from seed_search.catalog.artifacts import ArtifactStore
from seed_search.catalog.ingestion import atomic_json,strict_json_loads,verify_no_symlinks
from seed_search.catalog.registry import digest
from seed_search.catalog.models import identity,validate_observation_v2
from seed_search.catalog.extract import extract_observation_v2


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,required=True);parser.add_argument('--cohort',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--seconds',type=int,default=600)
    parser.add_argument('--resume',action='store_true');args=parser.parse_args()
    if not 10<=args.seconds<=600:raise ValueError('Explicit allocation must be10..600seconds')
    from seed_search import _native
    from seed_search.backend import Backend,biome_name,native_runtime,model_metadata,configure_native_threads
    from seed_search.realm.biomes import canonical
    from seed_search.realm.native_identity import native_source_fingerprint
    cohort=strict_json_loads(args.cohort.read_bytes());rows=cohort['rows']
    if not 1<=len(rows)<=200:raise ValueError('Fixed cohort capped at200existing worlds')
    native_runtime();configure_native_threads(1)
    template=identity('0',model_id=model_metadata()['model'],native_sha256=hashlib.sha256(Path(_native.__file__).read_bytes()).hexdigest(),source_sha256=native_source_fingerprint())
    root=verify_no_symlinks(args.output.absolute());progress_path=root/'progress.json'
    if root.exists() and not args.resume:raise ValueError('Existing output needs explicit --resume allocation')
    root.mkdir(parents=True,exist_ok=True);store=ArtifactStore(root/'objects')
    source_root=verify_no_symlinks(args.source_root.absolute());source=ArtifactStore(source_root/'artifacts')
    state=strict_json_loads(progress_path.read_bytes()) if progress_path.exists() else dict(revision='catalog-calibration-enrichment-v1',cohort_id=cohort['cohort_id'],identity=template,worlds=[],allocations=[])
    if state['cohort_id']!=cohort['cohort_id'] or state['identity']!=template:raise ValueError('Cohort/native identity changed')
    started=time.monotonic();deadline=started+args.seconds;stop=threading.Event()
    state['allocations'].append(dict(seconds=args.seconds,started_utc=time.time(),explicit_resume=args.resume));atomic_json(progress_path,state)
    resource.setrlimit(resource.RLIMIT_CPU,(args.seconds+5,args.seconds+10))
    try:os.nice(10)
    except OSError:pass
    def watchdog():
        while not stop.wait(.2):
            peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024)
            if peak>4<<30 or time.monotonic()>deadline+2:os._exit(124)
    threading.Thread(target=watchdog,daemon=True).start()
    checkpoint=root/'partial-observation.json'
    try:
        with sqlite3.connect((source_root/'pilot.sqlite').as_uri()+'?mode=ro',uri=True) as db:
            for row in rows[len(state['worlds']):]:
                if time.monotonic()>=deadline-5:break
                ident=dict(template,seed=row['seed']);previous=None
                if checkpoint.exists():
                    previous=validate_observation_v2(strict_json_loads(checkpoint.read_bytes()))
                    if previous['identity']!=ident:raise ValueError('Partial checkpoint seed/identity differs')
                with Backend(row['seed']) as backend:
                    obs=extract_observation_v2(ident,backend,name_for_id=lambda raw:canonical(biome_name(raw)),previous=previous)
                    atomic_json(checkpoint,obs)
                    complete=True
                    for y in (-48,0,160):
                        positions={tuple(p[:3]) for p in obs['biomes']['overworld']}
                        coords=[[x,y,z] for z in range(-5120,5120,64) for x in range(-5120,5120,64) if (x,y,z) not in positions]
                        for offset in range(0,len(coords),1024):
                            if time.monotonic()>=deadline-5:complete=False;break
                            batch=coords[offset:offset+1024];values=backend.biome_points(batch,dimension=0)
                            if len(values)!=len(batch):raise ValueError('Truncated calibration lattice')
                            for xyz,raw in zip(batch,values):
                                raw=int(raw);name=canonical(biome_name(raw));key=str(raw)
                                if key in obs['biome_names'] and obs['biome_names'][key]!=name:raise ValueError('Biome namespace changed')
                                obs['biome_names'][key]=name;obs['biomes']['overworld'].append(xyz+[raw])
                        atomic_json(checkpoint,validate_observation_v2(obs))
                        if not complete:break
                if not complete:break
                fields=db.execute('''SELECT a.sha256,a.relative_key,a.byte_length,a.uncompressed_length,a.codec
                    FROM observation_ref o JOIN artifact_ref a ON a.sha256=o.manifest_sha256 WHERE o.snapshot_id=? AND o.world_id=?''',
                    (cohort['snapshot_id'],row['world_id'])).fetchone()
                if fields is None:raise ValueError('Missing original observation')
                old=source.get_json(dict(zip(['sha256','relative_key','byte_length','uncompressed_length','codec'],fields)))
                if digest(old)!=row['observation_id']:raise ValueError('Original cohort observation changed')
                old_identity=dict(old['identity']);old_identity['native_sha256']=template['native_sha256']
                if old_identity!=ident:raise ValueError('Source/model differs beyond compiler/binary identity')
                old_plane={(x,y,z):bid for x,y,z,bid in old['biomes']}
                fresh={(x,y,z):bid for x,y,z,bid in obs['biomes']['overworld'] if y==63}
                differences=sum(fresh.get(xyz)!=bid for xyz,bid in old_plane.items())
                counts_changed={f:len(old['structures'][f])-len(obs['structures'].get(f,[])) for f in old['structures'] if old['structures'][f]!=obs['structures'].get(f,[])}
                if differences or counts_changed:raise ValueError(f'Compiler/source parity differs:biomes={differences},structures={counts_changed}')
                obs['metrics']['calibration']=dict(cohort_id=cohort['cohort_id'],legacy_observation_id=row['observation_id'],legacy_native_sha256=old['identity']['native_sha256'],lattice_y63_parity_points=len(old_plane),structure_inventory_parity=True)
                artifact=store.put_json(validate_observation_v2(obs))
                state['worlds'].append(dict(world_id=row['world_id'],seed=row['seed'],split=row['split'],observation_id=digest(obs),artifact=artifact))
                atomic_json(progress_path,state);checkpoint.unlink()
                if len(state['worlds'])%10==0:print(json.dumps(dict(completed=len(state['worlds']),total=len(rows),elapsed=round(time.monotonic()-started,2))),flush=True)
        state['last_elapsed_seconds']=time.monotonic()-started;state['complete']=len(state['worlds'])==len(rows);atomic_json(progress_path,state)
        print(json.dumps(dict(completed=len(state['worlds']),total=len(rows),complete=state['complete'],elapsed=state['last_elapsed_seconds'])),flush=True)
    finally:stop.set()


if __name__=='__main__':main()
