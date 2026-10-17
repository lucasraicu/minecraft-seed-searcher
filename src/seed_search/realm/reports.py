"""Streaming full candidate exports and independently ranked variant views."""
import csv
import json
import math
import copy
from contextlib import contextmanager
import fcntl
import hashlib
import os
from pathlib import Path
import shutil
import sqlite3
import time
import uuid

from .store import canonical


def _ranked(store, variant='baseline', limit=20):
    if variant=='baseline':
        from .leaderboard import rows
        result=[]
        for encoded,score,tier,misses in rows(store.db,limit):
            row=json.loads(encoded)
            near=(row.get('retention') or {}).get('classification')=='NEAR_MISS'
            row['smart_score']=score
            row['unmet_requirements']=misses if near else None
            row['leaderboard_rank']=len(result)+1
            row['ranking_view']='observed_partial_predictor_score; near miss' if near else 'complete_predictor_score' if row.get('baseline_score_complete',True) else 'provisional_interval_midpoint; inventory pending'
            result.append(row)
        return result
    elif variant in ('v1','v2'):
        # Only a complete score with verified weighted components replaces prediction.
        actual="json_extract(result,'$.result.actual_evaluation.score_verified_complete')=1"
        sql=f"""SELECT result FROM variants WHERE variant=? ORDER BY
            CASE WHEN {actual} OR json_extract(result,'$.result.score_verified_complete')=1 THEN 0
                 WHEN json_extract(result,'$.result.evidence')='PREDICTED' THEN 1 ELSE 2 END,
            CASE WHEN {actual} THEN CASE json_extract(result,'$.result.actual_evaluation.geometry_pass') WHEN 1 THEN 0 ELSE 1 END
                 ELSE CASE json_extract(result,'$.result.geometry_pass') WHEN 1 THEN 0 ELSE 1 END END,
            CASE WHEN {actual} THEN CAST(json_extract(result,'$.result.actual_evaluation.score') AS REAL)
                 ELSE CAST(json_extract(result,'$.result.score') AS REAL) END DESC,candidate_id,center LIMIT ?"""
        rows=[json.loads(r[0]) for r in store.db.execute(sql,(variant,limit))]
        for row in rows:
            result=row['result'];generated=result.get('actual_evaluation',{})
            row['ranking_view']='verified' if generated.get('score_verified_complete') or result.get('score_verified_complete') else 'prediction' if result.get('score_generation_source')!='actual' else 'actual_partial'
            row['ranking_result']=generated if generated.get('score_verified_complete') else result
        return rows
    else:raise ValueError('Results variant must be baseline, v1 or v2')


def _export_files(store, root, output):
    counts={}
    for variant in ('baseline','v1','v2'):
        rows=store.iter_candidates(include_score=True) if variant=='baseline' else store.iter_variants(variant=variant)
        # JSONL preserves all nested evidence; CSV contains independently useful summaries.
        fields=['candidate_id','seed','stronghold','evaluation_center','predicted_strongholds','screening_revision',
                'deficit_categories','fatal_reasons','marine_status','spawn_status','suggested_spawn','player_inspections','actual_generation_status',
                'variant','center','qualification','data_status',
                'smart_score',
                'retention_classification','unmet_requirements','pending_reasons','score','score_status','inventory_status','predicted_score','actual_partial_score','verified_score','geometry_score','border_fit','final_nether_status',
                'surface_wooded_requirement','surface_wooded_families','surface_bonus_interval','raw_record']
        with (root/f'{variant}.jsonl').open('w') as js,(root/f'{variant}.csv').open('w',newline='') as csvfile:
            writer=csv.DictWriter(csvfile,fieldnames=fields);writer.writeheader();n=0
            for row in rows:
                record=row.get('result',row)
                cid=row.get('candidate_id',row.get('id'))
                if variant!='baseline':
                    candidate=json.loads(store.db.execute('SELECT result FROM candidates WHERE id=?',(cid,)).fetchone()[0])
                    row={**row,'baseline':candidate}
                else:candidate=row
                surface=candidate.get('surface_biome_verification',{})
                surface_classification=surface.get('classification',{})
                smart_score=row.get('smart_score') if variant=='baseline' else None
                encoded=json.dumps(row,allow_nan=False,separators=(',',':'))
                js.write(encoded+'\n')
                starts=candidate.get('predicted_strongholds')
                writer.writerow({'candidate_id':cid,'seed':candidate['seed'],
                                 'stronghold':json.dumps(starts[0] if starts else None if candidate.get('evaluation_center') is not None else candidate['stronghold']),
                                 'evaluation_center':json.dumps(candidate.get('evaluation_center')),
                                 'predicted_strongholds':json.dumps(starts),
                                 'screening_revision':candidate.get('screening_revision'),
                                 'deficit_categories':json.dumps(candidate.get('deficit_categories',[])),
                                 'fatal_reasons':json.dumps(candidate.get('fatal_reasons',[])),
                                 'marine_status':(candidate.get('marine_stage') or {}).get('status','DEFERRED'),
                                 'spawn_status':(candidate.get('spawn_stage') or {}).get('status','PENDING'),
                                 'suggested_spawn':json.dumps(candidate.get('suggested_spawn')),
                                 'player_inspections':json.dumps(candidate.get('player_inspections')),
                                 'actual_generation_status':(candidate.get('actual_generation_verification') or {}).get('status','PENDING'),
                                 'variant':variant,'center':json.dumps(record.get('center')),
                                 'qualification':record.get('qualification'),'data_status':record.get('evidence',record.get('data_status')),
                                 'smart_score':smart_score,
                                 'retention_classification':(candidate.get('retention') or {}).get('classification'),
                                 'unmet_requirements':(candidate.get('retention') or {}).get('unmet_requirements'),
                                 'pending_reasons':json.dumps(candidate.get('pending_reasons',[])),
                                 'score':record.get('score',record.get('baseline_score')),
                                 'score_status':record.get('baseline_score_status',record.get('score_component_status')),
                                 'inventory_status':(candidate.get('inventory') or {}).get('status','legacy'),
                                 'predicted_score':record.get('predicted_score'),
                                 'actual_partial_score':record.get('actual_partial_score'),'verified_score':record.get('verified_score'),'geometry_score':record.get('geometry_score'),
                                 'border_fit':json.dumps(record.get('border_fit')),
                                 'final_nether_status':candidate.get('final_nether_status'),
                                 'surface_wooded_requirement':surface.get('wooded_requirement'),
                                 'surface_wooded_families':json.dumps(surface_classification.get('wooded_families',[])),
                                 'surface_bonus_interval':json.dumps(((surface_classification.get('uncertainty') or {}).get('actual_generation_score_interval'))),
                                 'raw_record':encoded})
                n+=1
        counts[variant]=n
    structure_rows=0
    with (root/'structure_starts.csv').open('w',newline='') as handle:
        fields=['candidate_id','seed','screening_revision','structure','dimension','x','y','z','predicted_viable',
                'horizontal_distance_blocks','distance_frame','hub_x','hub_z','hub_kind',
                'evidence_status','actual_generation_status']
        writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader()
        for candidate in store.iter_candidates():
            center=candidate.get('evaluation_center',candidate['stronghold'])
            for group,dimension in (('required_structures','overworld'),('required_nether_structures','nether'),('optional_structures','overworld')):
                for name,observation in candidate.get(group,{}).items():
                    hub=[center[0]/8,center[1]/8] if dimension=='nether' else center
                    viable={tuple(point[:2]) for point in observation.get('predicted_viable',[]) if isinstance(point,(list,tuple)) and len(point)>=2}
                    raw={tuple(point[:2]) for point in observation.get('raw',[]) if isinstance(point,(list,tuple)) and len(point)>=2}
                    for point in sorted(raw|viable):
                        if not isinstance(point,(list,tuple)) or len(point)<2:continue
                        x,z=point[:2]
                        writer.writerow({'candidate_id':candidate['id'],'seed':candidate['seed'],
                            'screening_revision':candidate.get('screening_revision'),'structure':name,
                            'dimension':dimension,'x':x,'y':'','z':z,'predicted_viable':point in viable,
                            'horizontal_distance_blocks':round(math.hypot(x-hub[0],z-hub[1]),3),
                            'distance_frame':'nether block coordinates' if dimension=='nether' else 'overworld block coordinates',
                            'hub_x':hub[0],'hub_z':hub[1],
                            'hub_kind':'fixed_world_origin' if candidate.get('evaluation_center')==[0,0] else 'candidate_center',
                            'evidence_status':observation.get('data_status','PREDICTED'),
                            'actual_generation_status':(candidate.get('actual_generation_verification') or {}).get('status','PENDING')})
                        structure_rows+=1
    summary={'status':store.status(),'exported_records':counts,'output':str(output.resolve())}
    summary['structure_start_rows']=structure_rows
    (root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    lines=['Realm candidate results','',f"Distinct full64 inputs committed: {summary['status']['completed_seeds']}",
           'Predictions and unknown evidence remain separate from actual-generation verification.','']
    for variant in ('baseline','v1','v2'):
        lines.append(f'{variant}: {counts[variant]} saved records')
        for row in _ranked(store,variant,10):
            r=row.get('ranking_result',row.get('result',row))
            lines.append(f"- {row.get('candidate_id',row.get('id'))}: {r.get('qualification')}; score {row.get('smart_score',r.get('score',r.get('baseline_score')))}; border {r.get('border_fit','not evaluated')}")
            if variant=='baseline' and row.get('suggested_spawn'):
                suggestion=row['suggested_spawn']
                lines.append(f"  Community spawn suggestion: {suggestion.get('coordinates')}; {suggestion['status']}; biome sample Y is not verified ground height or safety.")
            if variant=='baseline' and row.get('player_inspections'):
                lines.append('  Optional inspections: '+', '.join(f"{name}: {evidence['status']}" for name,evidence in row['player_inspections'].items()))
            if variant=='baseline' and row.get('surface_biome_verification'):
                surface=row['surface_biome_verification']
                lines.append(f"  Actual surface wooded requirement: {surface['wooded_requirement']}; families {', '.join(surface['classification']['wooded_families'])}; point samples cannot establish absence.")
        lines.append('')
    (root/'SUMMARY.md').write_text('\n'.join(lines)+'\n')
    return summary



def ensure_score_revision_complete(store):
    """Reject mixed-score views while a bounded rescore revision remains incomplete."""
    revision=store.get_state('rescore_revision')
    if revision and revision.get('status')!='complete':
        raise ValueError('Incomplete score revision; resume rescore with its saved policy before ranking, export or generation')


@contextmanager
def _read_snapshot(store):
    snapshot=copy.copy(store)
    snapshot.db=sqlite3.connect((store.run/'realm.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
    try:
        snapshot.db.execute('BEGIN')
        ensure_score_revision_complete(snapshot)
        yield snapshot
    finally:
        snapshot.db.close()


@contextmanager
def _rescore_lock(store):
    with (store.run/'.realm-scan.lock').open('a+') as lock:
        try:
            fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError('Another scanner or rescore owns this run') from exc
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(),fcntl.LOCK_UN)


def ranked(store, variant='baseline', limit=20):
    with _read_snapshot(store) as snapshot:
        return _ranked(snapshot,variant,limit)


def _fsync_directory(path):
    fd=os.open(path,os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _sync_file(path):
    with path.open('rb') as handle:
        os.fsync(handle.fileno())


def _write_manifest(generation, metadata):
    files={}
    for path in sorted(generation.iterdir()):
        if path.is_file() and path.name!='manifest.json':
            digest=hashlib.sha256()
            with path.open('rb') as handle:
                for chunk in iter(lambda:handle.read(1<<20),b''):
                    digest.update(chunk)
            files[path.name]={'bytes':path.stat().st_size,'sha256':digest.hexdigest()}
            _sync_file(path)
    manifest={**metadata,'files':files}
    (generation/'manifest.json').write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n')
    _sync_file(generation/'manifest.json')
    _fsync_directory(generation)
    return manifest


def _publish_pointer(root,generation):
    temporary=root/f'.current-{uuid.uuid4().hex}'
    try:
        temporary.symlink_to(generation.relative_to(root),target_is_directory=True)
        os.replace(temporary,root/'current')
        _fsync_directory(root)
    finally:
        temporary.unlink(missing_ok=True)


EXPORT_FILES=('baseline.jsonl','baseline.csv','v1.jsonl','v1.csv','v2.jsonl','v2.csv','structure_starts.csv','summary.json','SUMMARY.md','manifest.json')


def _prepare_compatibility_paths(root):
    """Migrate prior flat exports without changing their bytes before publication."""
    current=root/'current'
    old=[root/name for name in EXPORT_FILES if (root/name).is_file() and not (root/name).is_symlink()]
    if old:
        legacy=root/'.generations'/f'legacy-{uuid.uuid4().hex}'
        legacy.mkdir()
        # A partial earlier migration has links to current; copy that complete view too.
        for name in EXPORT_FILES:
            source=root/name
            if source.is_file():
                shutil.copyfile(source,legacy/name)
        if not (legacy/'manifest.json').exists():
            _write_manifest(legacy,{'generation':legacy.name,'kind':'legacy-export-migration'})
        else:
            for path in legacy.iterdir():
                _sync_file(path)
            _fsync_directory(legacy)
        _publish_pointer(root,legacy)
    for name in EXPORT_FILES:
        destination=root/name
        target=Path('current')/name
        if destination.is_symlink() and os.readlink(destination)==str(target):
            continue
        temporary=root/f'.alias-{uuid.uuid4().hex}'
        try:
            temporary.symlink_to(target)
            os.replace(temporary,destination)
        finally:
            temporary.unlink(missing_ok=True)
    _fsync_directory(root)


@contextmanager
def _export_lock(root):
    with (root/'.export.lock').open('a+') as lock:
        try:
            fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError('Another export owns this output directory') from exc
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(),fcntl.LOCK_UN)


def export(store, output=None):
    """Publish one immutable complete export generation through an atomic pointer.

    Stable root paths resolve through current; multi-file consumers must resolve
    current once and read the pinned generation to avoid crossing a later switch.
    """
    root=Path(output or store.run/'results').resolve()
    root.mkdir(parents=True,exist_ok=True)
    with _export_lock(root):
        return _export_generation(store,root)


def _export_generation(store,root):
    generations=root/'.generations';generations.mkdir(exist_ok=True)
    generation=generations/f'export-{uuid.uuid4().hex}'
    generation.mkdir()
    try:
        with _read_snapshot(store) as snapshot:
            summary=_export_files(snapshot,generation,root)
            summary['generation']=generation.name
            summary['generation_path']=str(generation)
            (generation/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
            if not all((generation/name).is_file() for name in EXPORT_FILES if name!='manifest.json'):
                raise ValueError('Export generation is missing required files')
            revision=snapshot.get_state('rescore_revision')
            identity=snapshot.get_state('identity')
            _write_manifest(generation,{'generation':generation.name,'kind':'complete-export','status':'complete',
                'created_at':time.time(),'score_revision':revision,'source_identity_sha256':hashlib.sha256(canonical(identity).encode()).hexdigest(),
                'exported_records':summary['exported_records'],'completed_seeds':summary['status']['completed_seeds']})
        _fsync_directory(generations)
        _prepare_compatibility_paths(root)
        _publish_pointer(root,generation)
        return summary
    except BaseException:
        # Complete-but-unpublished generations are safe to retain for inspection.
        # Incomplete staging directories are never made current.
        raise


def _candidate_rescore(candidate,policy,revision_id):
    if candidate.get('contract')=='master_seed_blueprint_v1':
        from .config import dynamic_policy
        if dynamic_policy(candidate):
            from .config import dynamic_v2_policy, dynamic_v3_policy
            cfg = policy if (policy and dynamic_policy(policy)) else candidate
            if dynamic_v3_policy(cfg) or dynamic_v2_policy(cfg):
                is_v3 = dynamic_v3_policy(cfg)
                from .blueprint import dynamic_v2_score, dynamic_v3_score, score_uncertainty
                from .dynamic import (hub_bonus_v2, hub_bonus_v3, hub_village_v2,
                                      weighted_radial_v2, weighted_radial_v3,
                                      village_spread_bonus_v2, retained_scenic_pair_v2,
                                      treasure_bastion_bonus_v2, nether_core_bonus_v3)
                import math
                center=candidate['evaluation_center']
                required=candidate['required_structures']
                structures={name:ob['predicted_viable'] for name,ob in required.items()}
                observations={**required,**candidate['required_nether_structures'],**candidate['optional_structures']}
                counts={name:len(ob['predicted_viable']) for name,ob in observations.items()}
                names=[s['biome'] for s in candidate['biomes']['sampling']['samples'] if s['coordinate'][1]==63]
                ow_half = 1024 if is_v3 else None
                nether_half = 512 if is_v3 else None
                hub=hub_bonus_v3(structures,center) if is_v3 else hub_bonus_v2(structures,center)
                scenic,scenic_witness,river_witness=retained_scenic_pair_v2(
                    candidate['biomes']['sampling']['samples'],center,overworld_half=ow_half)
                spread,triple=village_spread_bonus_v2(structures['village'],center,overworld_half=ow_half)
                variants=candidate.get('bastion_variants')
                if not isinstance(variants,list):
                    raise ValueError('Missing retained Bastion variants; re-evaluate this seed before rescoring')
                by_coordinate={(x,z):variant for x,z,variant in variants}
                bastions=candidate['required_nether_structures']['bastion']['predicted_viable']
                if any(tuple(p) not in by_coordinate for p in bastions):
                    raise ValueError('Incomplete retained Bastion variants; re-evaluate this seed before rescoring')
                tb,_=treasure_bastion_bonus_v2(bastions,center,lambda x,z:by_coordinate[(x,z)],nether_half=nether_half)
                targets=candidate.get('configured_targets') or (policy.get('structures',{}).get('minimum_counts') if policy else None)
                opt_counts={name:len(ob['predicted_viable']) for name,ob in candidate['optional_structures'].items()}
                if is_v3:
                    nether_points = {name: ob['predicted_viable'] for name, ob in candidate['required_nether_structures'].items()}
                    nether_core = nether_core_bonus_v3(nether_points, center)
                    score,components,deficits=dynamic_v3_score(
                        counts,
                        biome_names=names,
                        hub=hub,
                        scenic=scenic,
                        village_spread=spread,
                        treasure_bastion=tb,
                        optional_counts=opt_counts,
                        nether_core=nether_core,
                    )
                else:
                    score,components,deficits=dynamic_v2_score(counts,names,hub,scenic,spread,tb,opt_counts,targets=targets)
                radial=weighted_radial_v3(structures,center,overworld_half=ow_half) if is_v3 else weighted_radial_v2(structures,center)
                radial_key=int(math.floor(radial*1e6+0.5))
                orig_dist_sq=center[0]**2+center[1]**2
                origin=math.hypot(*center)
                update_fields=dict(baseline_score_observed=score,baseline_score=score,
                    baseline_score_uncertainty=score_uncertainty(score,[],True),score_revision=revision_id,
                    weighted_radial_dist=radial,origin_distance=origin,radial_key=radial_key,
                    origin_distance_squared=orig_dist_sq,deficit_penalty=components['deficit_penalty'],
                    bonus_total=components['bonus_total'],
                    hub_bonus=components.get('hub_bonus', 0),
                    scenic_bonus=int(25 if is_v3 and scenic else scenic),scenic_witness=list(scenic_witness) if scenic_witness else None,
                    river_witness=list(river_witness) if river_witness else None,
                    village_spread_bonus=int(25 if is_v3 and spread else spread),village_triple=[list(p) for p in triple] if triple else None,
                    treasure_bastion=int(bool(tb)),
                    starter_hub_village=hub_village_v2(structures,center),deficit_categories=deficits)
                if is_v3:
                    update_fields['nether_core_bonus']=components.get('nether_core_bonus', 0)
                candidate.update(update_fields)
                candidate['ranking']={**candidate.get('ranking',{}),'score':score,'final_score':score,
                    'deficit_tier':len(candidate['deficit_categories']),'weighted_radial_dist':radial,
                    'radial_key':radial_key,'origin_distance_squared':orig_dist_sq,'origin_distance':origin,
                    'components':components}
                return candidate
            from .blueprint import dynamic_score,score_uncertainty
            from .dynamic import hub_bonus,weighted_radial
            import math
            center=candidate['evaluation_center']
            required=candidate['required_structures']
            structures={name:ob['predicted_viable'] for name,ob in required.items()}
            observations={**required,**candidate['required_nether_structures'],**candidate['optional_structures']}
            counts={name:len(ob['predicted_viable']) for name,ob in observations.items()}
            names=[s['biome'] for s in candidate['biomes']['sampling']['samples'] if s['coordinate'][1]==63]
            hub=hub_bonus(structures,center);score=dynamic_score(counts,names,hub)
            radial=weighted_radial(structures,center);origin=math.hypot(*center)
            candidate.update(baseline_score_observed=score,baseline_score=score,
                baseline_score_uncertainty=score_uncertainty(score,[],True),score_revision=revision_id,
                weighted_radial_dist=radial,origin_distance=origin)
            candidate['ranking']={**candidate.get('ranking',{}),'score':score,
                'deficit_tier':len(candidate['deficit_categories']),'weighted_radial_dist':radial,'origin_distance':origin,
                'components':{**candidate.get('ranking',{}).get('components',{}),'hub_bonus':hub}}
            return candidate
        from .blueprint import smart_score,score_uncertainty
        from .config import river_policy,origin_policy,two_group_policy,marine_baseline_policy
        v2=two_group_policy(candidate)
        marine_baseline=marine_baseline_policy(candidate)
        names=(s['biome'] for s in ((candidate.get('biomes') or {}).get('sampling') or {}).get('samples',()) if s['coordinate'][1]==63)
        required=candidate['required_structures']
        optional=candidate['optional_structures']
        # Historical v2 terrain work may append marine inventories; v3 already
        # includes them in its baseline. Keep baseline and combined scores distinct.
        baseline_required={k:v for k,v in required.items() if k not in ('monument','shipwreck')} if v2 and not marine_baseline else required
        baseline_optional={k:v for k,v in optional.items() if k not in ('monument','shipwreck')} if v2 and not marine_baseline else optional
        ranking=smart_score(baseline_required,candidate['required_nether_structures'],baseline_optional,
                            locked=bool(candidate.get('screening_revision')),river=river_policy(candidate),
                            origin=origin_policy(candidate),two_group=v2,biome_names=names,river_bonus=not marine_baseline,
                            metrics=None if v2 else candidate.get('terrain_score_metrics'))
        candidate.update(baseline_score_observed=ranking['score'],
                         baseline_score=ranking['score'] if candidate['baseline_score_complete'] else None,
                         baseline_score_uncertainty=score_uncertainty(ranking['score'],
                             candidate.get('fatal_reasons',[])+candidate.get('biome_failures',[]) if v2 else candidate['pending_reasons'],
                             candidate['baseline_score_complete']),score_revision=revision_id)
        if v2 and (candidate.get('marine_stage') or {}).get('status') in ('PREDICTED','VERIFIED'):
            source=(candidate.get('terrain_status') or {}).get('source')
            actual=isinstance(source,dict) and source.get('kind')=='actual_generation'
            prior_ranking=candidate.get('ranking') or {}
            combined=smart_score(required,candidate['required_nether_structures'],optional,
                                 locked=True,river=river_policy(candidate),origin=True,two_group=True,river_bonus=not marine_baseline,
                                 biome_names=(s['biome'] for s in ((candidate.get('biomes') or {}).get('sampling') or {}).get('samples',()) if s['coordinate'][1]==63),
                                 metrics=candidate.get('terrain_score_metrics') if actual else None,
                                 coastal_footprint_verified=actual and prior_ranking.get('coastal_footprint_bonus_status')=='VERIFIED')
            candidate.update(ranking=combined,combined_score=combined['score'])
        else:
            candidate['ranking']=ranking
        return candidate
    from .biomes import classify
    from .baseline import baseline_score_uncertainty
    if candidate.get('biomes'):
        evidence=candidate['biomes'].get('uncertainty',{})
        detection=classify(candidate['biomes']['raw_names'],policy['biomes'],
                           complete=evidence.get('exhaustive_verified') is True,
                           verified=evidence.get('domain')=='actual_generated_surface')
        candidate['biomes'].update({k:detection[k] for k in ('wooded_bonus','family_bonuses','variant_bonuses','surface_bonus','score','uncertainty')})
        observed_score=detection['score']+sum(policy['structures']['optional_bonuses'].get(k,0) for k,v in candidate['optional_structures'].items() if v.get('predicted_viable'))
        candidate['baseline_score_observed']=observed_score
        candidate['baseline_score']=observed_score if candidate.get('baseline_score_complete',True) else None
        for key,observation in candidate['optional_structures'].items():
            observation['bonus']=policy['structures']['optional_bonuses'].get(key,0) if observation.get('predicted_viable') else 0
    candidate['baseline_score_uncertainty']=baseline_score_uncertainty(candidate.get('biomes'),candidate.get('optional_structures') or {},policy,candidate.get('pending_reasons',[]))
    surface=candidate.get('surface_biome_verification')
    if surface and surface.get('classification'):
        detected=surface['classification']
        # Keep actual point evidence separate from the predictor baseline score.
        surface['classification']=classify(detected['raw_names'],policy['biomes'],complete=False,
                                            verified=(detected.get('uncertainty') or {}).get('domain')=='actual_generated_surface')
        surface['wooded_requirement']=surface['classification']['qualification']
        surface['score_revision']=revision_id
    candidate['score_revision']=revision_id
    return candidate


def _variant_rescore(wrapper,candidate,policy,revision_id):
    from .terrain import apply_score_policy,attach_actual_evaluation
    result=wrapper['result']
    result['baseline_quality']=min(100,max(0,100*(candidate.get('baseline_score') if candidate.get('baseline_score') is not None else candidate.get('baseline_score_observed',0))/policy['scoring']['baseline_quality_cap']))
    apply_score_policy(result,policy['scoring'],component_status={'baseline_quality':candidate.get('qualification','PENDING') if candidate.get('baseline_score_complete',True) else 'PARTIAL'})
    if result.get('actual_evaluation'):
        actual=result['actual_evaluation']
        actual['baseline_quality']=result['baseline_quality']
        apply_score_policy(actual,policy['scoring'],source='actual',component_status={'baseline_quality':candidate.get('qualification','PENDING') if candidate.get('baseline_score_complete',True) else 'PARTIAL'})
        attach_actual_evaluation(result,actual,policy['scoring'])
    result['rescore_policy']=dict(policy['scoring'])
    result['score_revision']=revision_id
    return wrapper


def _validate_rescore_policy(store,policy):
    from .config import validate_config
    validate_config(policy)
    old=copy.deepcopy(store.identity['config']);new=copy.deepcopy(policy)
    for cfg in (old,new):
        cfg.pop('scoring',None)
        for section,key in (('structures','optional_bonuses'),('biomes','family_bonuses'),('biomes','variant_bonuses')):
            cfg[section].pop(key,None)
    if old!=new:
        raise ValueError('Rescore may change bonus weights and score weights; generation or eligibility settings require a separate run')


def rescore(store, policy, *, batch_size=256, progress=None):
    """Bounded generation-free rescore; restart the same policy to finish its revision."""
    if isinstance(batch_size,bool) or not isinstance(batch_size,int) or not 1<=batch_size<=4096:
        raise ValueError('Rescore batch_size must be between 1 and 4096')
    if store.db.in_transaction:
        raise ValueError('Finish the caller transaction before starting rescore')
    _validate_rescore_policy(store,policy)
    policy=copy.deepcopy(policy)
    policy_hash=hashlib.sha256(canonical(policy).encode()).hexdigest()
    with _rescore_lock(store):
        revision=store.get_state('rescore_revision')
        if revision and revision.get('status')!='complete':
            if revision['policy_sha256']!=policy_hash:
                raise ValueError('Another score revision is incomplete; resume its saved policy first')
        else:
            number=(revision or {}).get('number',0)+1
            revision={'id':f'{number}-{policy_hash[:16]}','number':number,'status':'running','phase':'candidates',
                      'candidate_cursor':'','variant_cursor':['','',''],'policy':policy,'policy_sha256':policy_hash,
                      'rescored_candidates':0,'rescored_variants':0}
            store.set_state('rescore_revision',revision)
        while revision['phase']=='candidates':
            rows=store.db.execute('SELECT id,result FROM candidates WHERE id>? ORDER BY id LIMIT ?',
                                  (revision['candidate_cursor'],batch_size)).fetchall()
            if not rows:
                revision={**revision,'phase':'variants'}
                store.set_state('rescore_revision',revision)
                break
            updated=[]
            count=0
            for cid,payload in rows:
                candidate=json.loads(payload)
                count+=int(bool(candidate.get('biomes')))
                updated.append((canonical(_candidate_rescore(candidate,policy,revision['id'])),cid))
            next_revision={**revision,'candidate_cursor':rows[-1][0],
                           'rescored_candidates':revision['rescored_candidates']+count}
            with store.db:
                store.db.executemany('UPDATE candidates SET result=? WHERE id=?',updated)
                store._set('rescore_revision',next_revision)
            revision=next_revision
            if progress:
                progress(copy.deepcopy(revision))
        while revision['phase']=='variants':
            rows=store.db.execute('SELECT candidate_id,variant,center,result FROM variants WHERE (candidate_id,variant,center)>(?,?,?) ORDER BY candidate_id,variant,center LIMIT ?',
                                  (*revision['variant_cursor'],batch_size)).fetchall()
            if not rows:
                break
            updated=[]
            for cid,variant,center,payload in rows:
                candidate=store.get_candidate(cid)
                wrapper=_variant_rescore(json.loads(payload),candidate,policy,revision['id'])
                updated.append((canonical(wrapper),cid,variant,center))
            next_revision={**revision,'variant_cursor':list(rows[-1][:3]),
                           'rescored_variants':revision['rescored_variants']+len(rows)}
            with store.db:
                store.db.executemany('UPDATE variants SET result=? WHERE candidate_id=? AND variant=? AND center=?',updated)
                store._set('rescore_revision',next_revision)
            revision=next_revision
            if progress:
                progress(copy.deepcopy(revision))
        from .terrain import terrain_scoring_identity
        finished={**revision,'status':'complete','phase':'complete'}
        with store.db:
            store._set('score_policy',policy)
            store._set('rescore_revision',finished)
            if store.get_state('terrain_scoring_identity') is not None:
                store._set('terrain_scoring_identity',terrain_scoring_identity(policy))
        has_top_table = store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='top_candidates'").fetchone() is not None
        top50_file = store.run / 'top50.json' if hasattr(store, 'run') and store.run else None
        if has_top_table or (top50_file and top50_file.exists()):
            from .top_tracker import Top50Tracker
            pipeline=store.get_state('native_pipeline') or {}
            tracker = Top50Tracker(capacity=pipeline.get('top_k') or 50)
            rows = store.db.execute('SELECT result FROM candidates').fetchall()
            for (payload,) in rows:
                candidate = json.loads(payload)
                seed_str = str(candidate.get('seed', ''))
                record = {'seed': seed_str, 'anchors': [candidate]}
                tracker.observe(record)
            if has_top_table:
                tracker.flush(store.db)
            if top50_file:
                tracker.save_to_json(str(top50_file))
        return {'rescored_candidates':finished['rescored_candidates'],'rescored_variants':finished['rescored_variants'],
                'generation_queries':0,'score_revision':finished['id']}
