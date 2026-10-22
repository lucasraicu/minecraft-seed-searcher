#!/usr/bin/env python3
"""Import bounded, independently reviewed BDS audit results as separate evidence.

Never re-extract a seed or change predictor observations/rankings. Only the pinned
BDS audit protocol is supported; command mismatches and conflicting runs fail closed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from seed_search.catalog.models import observation_id
from seed_search.catalog.segments import SegmentedCatalog
from seed_search.catalog.evidence import build_evidence,write_evidence

IMAGE_SHA='cf479afd0ab8a8bb095f7aa71fd42064cf5ba7aff6c8a8f4f5503aac826511d8'
BUILD='1.26.52.3'
COMMANDS=dict(village='village',trial_chamber='trial_chambers',ancient_city='ancient_city',
 mansion='mansion',monument='monument',outpost='pillager_outpost',desert_pyramid='temple',
 jungle_temple='temple',swamp_hut='temple',igloo='temple',trail_ruins='trail_ruins',
 ruined_portal='ruined_portal',shipwreck='shipwreck',mineshaft='mineshaft')
LOCATE=re.compile(r'The nearest minecraft:([a-z_]+) is at block (-?\d+), \(y\?\), (-?\d+)')


def _unique(pairs):
    d={}
    for k,v in pairs:
        if k in d:raise ValueError('Duplicate JSON key')
        d[k]=v
    return d


def _load(path):
    path=Path(path)
    if path.is_symlink():raise ValueError('Audit report cannot be a symlink')
    with path.open('rb') as f:data=f.read((16<<20)+1)
    if len(data)>16<<20:raise ValueError('Oversized audit report')
    result=json.loads(data,object_pairs_hook=_unique,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))
    return result,hashlib.sha256(data).hexdigest()


def collect(root,snapshot_id,report_paths):
    if not 1<=len(report_paths)<=32:raise ValueError('Supply1..32 reports')
    groups={};skipped=0
    with SegmentedCatalog(root) as store:
        store.info(snapshot_id);store._verified_membership(snapshot_id)
        for path in map(Path,report_paths):
            report,sha=_load(path)
            if report.get('status')!='observed' or report.get('clean_shutdown') is not True or report.get('owned_container_removed') is not True:
                raise ValueError('Audit must finish with observed results and confirmed cleanup')
            controls=report['controls'];seed=controls['seed']
            if controls['image_id']!='sha256:'+IMAGE_SHA or report['world_identity']['seed']!=seed:
                raise ValueError('Pinned image or observed seed mismatch')
            logs=path.parent/'console.log'
            if logs.is_symlink() or logs.stat().st_size>32<<20:raise ValueError('Invalid audit console log')
            if not re.search(r'\bVersion: '+re.escape(BUILD)+r'(?:\s|$)',logs.read_text()):raise ValueError('Actual BDS version line is missing')
            properties=path.parent/'worlds/world/server.properties'
            if properties.is_symlink() or properties.stat().st_size>65536:raise ValueError('Invalid audit settings')
            settings=properties.read_bytes();settings_sha=hashlib.sha256(settings).hexdigest()
            if ('level-seed='+seed).encode() not in settings.splitlines():raise ValueError('Audit settings seed mismatch')
            if controls.get('settings_sha256',settings_sha)!=settings_sha:raise ValueError('Audit settings checksum mismatch')
            refs=store.conn.execute('SELECT world_id,observation_id FROM observation_ref WHERE snapshot_id=? AND seed=?',(snapshot_id,seed)).fetchall()
            if len(refs)!=1:raise ValueError('Audit seed is not uniquely represented in snapshot')
            wid,oid=refs[0];source=controls['prediction']
            if source['world_id']!=wid or source.get('observation_id',oid)!=oid:raise ValueError('Audit source identity mismatch')
            if wid not in groups:
                obs=store.observation(snapshot_id,wid)
                if observation_id(obs)!=oid:raise ValueError('Observation hash mismatch')
                groups[wid]=dict(obs=obs,settings=settings_sha,reports=set(),structures={},biomes={})
            group=groups[wid]
            if group['settings']!=settings_sha:raise ValueError('Conflicting game settings across audit reports')
            group['reports'].add(sha)
            source_points={fid:{tuple(p) for p in points} for fid,points in group['obs']['structures'].items()}
            biome_points={tuple(p[:3]) for p in group['obs']['biomes']}
            for q in report['queries']:
                kind=q['kind'];fid='structure.village' if kind=='predicted' else kind
                if fid not in source_points:skipped+=1;continue
                if tuple(q['query']) not in source_points[fid]:raise ValueError('Candidate query is outside its bound observation')
                if q.get('dimension','overworld')!='overworld':raise ValueError('Catalog audit uses wrong dimension')
                command=COMMANDS[fid.split('.')[1]]
                if q.get('command_id',command)!=command:raise ValueError('Feature/command mismatch')
                matches=[LOCATE.search(line) for line in q['output'] if LOCATE.search(line)]
                if len(matches)>1:raise ValueError('Ambiguous locate response')
                reported=None
                if matches:
                    m=matches[0]
                    if m.group(1)!=command:raise ValueError('Response command differs from request')
                    reported=list(map(int,m.groups()[1:]))
                    outcome='located_exact' if reported==q['query'] else 'coordinate_difference'
                else:
                    outcome='no_location' if any('No valid structure found' in line or 'Could not find' in line for line in q['output']) else 'error'
                row=dict(feature_id=fid,command_id=command,predicted=q['query'],reported=reported,outcome=outcome)
                key=(fid,*q['query']);previous=group['structures'].get(key)
                if previous is not None and previous!=row:raise ValueError('Conflicting repeated structure observations')
                group['structures'][key]=row
            for batch in report.get('biome_batches',[]):
                if batch['chunksAfterUnload']!=0:raise ValueError('Biome batch failed owned ticking-area cleanup')
                for q in batch['rows']:
                    point=(q['x'],q['y'],q['z'])
                    if q.get('dimension','overworld')!='overworld' or point not in biome_points:skipped+=1;continue
                    row=dict(position=list(point),observed_name=q.get('id'),outcome='error' if 'error' in q else 'observed')
                    previous=group['biomes'].get(point)
                    if previous is not None and previous!=row:raise ValueError('Conflicting repeated biome observations')
                    group['biomes'][point]=row
        payloads=[]
        for wid,group in sorted(groups.items()):
            verifier=dict(edition='bedrock',game_build_id=BUILD,image_sha256=IMAGE_SHA,script_api='2.10.0',
                          settings_sha256=group['settings'],report_sha256s=sorted(group['reports']))
            payloads.append(build_evidence(group['obs'],snapshot_id,verifier,
                [v for _,v in sorted(group['structures'].items())],[v for _,v in sorted(group['biomes'].items())]))
    return payloads,skipped


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    p.add_argument('--snapshot',required=True);p.add_argument('--report',type=Path,action='append',required=True)
    p.add_argument('--dry-run',action='store_true');args=p.parse_args(argv)
    payloads,skipped=collect(args.root,args.snapshot,args.report)
    result=[]
    for payload in payloads:
        path=None if args.dry_run else str(write_evidence(args.root,payload))
        result.append(dict(world_id=payload['world_id'],structure_checks=len(payload['structure_checks']),
                           biome_checks=len(payload['biome_checks']),path=path))
    print(json.dumps(dict(dry_run=args.dry_run,worlds=result,skipped_outside_catalog_predicates=skipped),indent=2))
    return 0

if __name__=='__main__':raise SystemExit(main())
