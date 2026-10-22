# Narrow final correction review
Read-only High source review, no tools/edits/commands. Approved scope already includes performance/legacy parity and bounded migration; no newplanapproval. Original222migration3150.624seconds of3600 completed. Firstcoldqueryfailed10s. Newcorrection uses remaining449.376seconds, copies immutablehistory and fixesper-modelegacycollision in a NEW policyroot; no rawobservations/native/Realm/scoring/filtersemanticschange. Standard JSON packedderivedprojections underexisting16MiBcap, no customDB. Existing immutableCAS checksum/sourcebinding+writer-validator trust principle retained: trustedV4 already skippedfullnumericvalidation; trustedV5checksstructuralshapes/masks/sourceheader and usesvalidatedwriterdata. Stalevalidatorfullcodec path unchanged. Query code drops two duplicate manifestdigestcomputations because snapshot(sid) alreadyverifiesdigest ==sid. Deadline remains10s.

The sourcefix mapsprovidedbaselegacyrows by(anchor,side,tuple(anchor_modes)) instead ofonlycoordinates; exact per-modelegacy matterswhenspawncollideswithorigin/grid. V3layoutIDalreadybindsmodes. Newcorrection restores originallegacypayloads byexactmodekeyand reoffersalllegacyfamilies acrossall222savedworlds fromoriginalV2grid. Currentnonlegacyv2/v3/productTop2Kmemberships reused: theirfeatures/rankswerenotaffected. Originalreceipts/Realm evals reusedexact. Newrootpolicyhash includes correctedsummarysource. No rawre-extraction, newgamejobs, searches orpublicbackendadoptionyet.

    @staticmethod
    def _pack_query_rows(rows,definition):
        features=definition['features'];packed=[]
        for row in rows:
            blocks=[]
            for feature in features:
                block=row['features'][feature['id']]
                counts=block['counts']
                if feature['kind']=='biome_witness':counts=sum(int(bool(n))<<i for i,n in enumerate(counts))
                complete=sum(int(bool(n))<<i for i,n in enumerate(block['complete']))
                blocks.append([counts,complete,block['nearest_d2'],block['witness']])
            packed.append([row['layout_id'],row['anchor'],row['anchor_modes'],row['legacy'],blocks])
        return packed

    def _unpack_query_rows(self,rows,entry,definition,side,mode=None,*,validate=True):
        features=definition['features'];result=[];seen=set()
        count_bits=tuple(tuple(int(bool(n&(1<<i))) for i in range(4)) for n in range(16))
        complete_bits=tuple(tuple(bool(n&(1<<i)) for i in range(4)) for n in range(16))
        def mask(value):
            if type(value)is not int or not 0<=value<=15:raise ValueError('Invalid packed bitmask')
            return [bool(value&(1<<i)) for i in range(4)]
        for packed in rows:
            if not isinstance(packed,list) or len(packed)!=5:raise ValueError('Invalid packed query row')
            lid,anchor,modes,legacy,blocks=packed;self._sha(lid)
            if (lid in seen or not isinstance(anchor,list) or len(anchor)!=2 or any(type(n)is not int or abs(n)>30000000 for n in anchor)
                    or not isinstance(modes,list) or not modes or len(modes)!=len(set(modes)) or any(m not in ('origin','recommended','world_spawn_estimated','world_spawn_observed') for m in modes)
                    or not isinstance(legacy,dict) or not isinstance(blocks,list) or len(blocks)!=len(features)):raise ValueError('Invalid packed query scope')
            seen.add(lid)
            if mode is not None and mode not in modes:continue
            values={}
            for feature,block in zip(features,blocks):
                if not isinstance(block,list) or len(block)!=4:raise ValueError('Invalid packed feature block')
                counts,complete,distance,witness=block
                if feature['kind']=='biome_witness':
                    if type(counts)is not int or not 0<=counts<=15:raise ValueError('Invalid packed biome mask')
                    counts=list(count_bits[counts])
                elif not isinstance(counts,list) or len(counts)!=4 or (validate and any(type(n)is not int or not 0<=n<=200000 for n in counts)):raise ValueError('Invalid packed structure counts')
                if type(complete)is not int or not 0<=complete<=15:raise ValueError('Invalid packed completeness mask')
                complete=list(complete_bits[complete])
                if validate and distance is not None and (type(distance)is not int or not 0<=distance<=2*(60000000**2)):raise ValueError('Invalid packed distance')
                if validate and witness is not None and (not isinstance(witness,list) or len(witness)!=3 or any(type(witness[i])is not int or abs(witness[i])>30000000 for i in (0,2)) or (witness[1] is not None and (type(witness[1])is not int or not -64<=witness[1]<=319))):raise ValueError('Invalid packed XYZ witness')
                if (witness is None)!=(distance is None):raise ValueError('Incomplete packed witness')
                values[feature['id']]=dict(dimension=feature['dimension'],counts=counts,complete=complete,nearest_d2=distance,witness=witness)
            result.append(dict(revision='catalog-summary-v3',registry_revision=entry['registry_revision'],
                source_observation_id=entry['observation_id'],source_extension_id=entry['source_extension_id'],
                sampling_profile_revision=entry['sampling_profile_revision'],world_id=entry['world_id'],seed=entry['identity']['seed'],
                anchor=anchor,nether_anchor=[n//8 for n in anchor],anchor_modes=modes,border_side=side,layout_id=lid,features=values,legacy=legacy))
        return result

    def _projection(self,entry,side,mode=None):
        """The immutable snapshot binds this derived view to its verified raw bundle."""
        value=self.artifacts.get_json(entry['summary_artifacts'][str(side)])
        fields={'revision','world_id','identity','observation_id','bundle_sha256','border_side','rows'}
        if (not isinstance(value,dict) or
                (value.get('revision'),frozenset(value)) not in (
                    ('catalog-query-projection-v2',frozenset(fields)),
                    ('catalog-query-projection-v3',frozenset(fields|{'summary_validator_sha256','row_count'})),
                    ('catalog-query-projection-v4',frozenset(fields|{'summary_validator_sha256','row_count','registry','sampling_profile_revision','source_extension_id'})),
                    ('catalog-query-projection-v5',frozenset(fields|{'summary_validator_sha256','row_count','registry','sampling_profile_revision','source_extension_id'})))
                or any(value[k]!=entry[k] for k in ('world_id','identity','observation_id'))
                or value['bundle_sha256']!=entry['artifact']['sha256'] or value['border_side']!=side
                or not isinstance(value['rows'],list) or len(value['rows'])>1024):raise ValueError('Invalid query projection binding')
        v3=value['revision'] in ('catalog-query-projection-v4','catalog-query-projection-v5')
        current=value['revision'] in ('catalog-query-projection-v3','catalog-query-projection-v4','catalog-query-projection-v5')
        if v3 and (registry.digest(value['registry'])!=entry['registry_revision'] or any(value[k]!=entry[k] for k in ('sampling_profile_revision','source_extension_id'))):raise ValueError('Projected v3evidence differs')
        if current:
            self._sha(value['summary_validator_sha256'])
            if type(value['row_count']) is not int or value['row_count']!=len(value['rows']):raise ValueError('Projection row count mismatch')
        trusted=current and value['summary_validator_sha256']==self._query_validator_id()
        if value['revision']=='catalog-query-projection-v5':
            value=dict(value,rows=self._unpack_query_rows(value['rows'],entry,value['registry'],side,mode,validate=not trusted))
        seen=set()
        for row in value['rows']:
            if (not isinstance(row,dict) or row.get('world_id')!=entry['world_id'] or row.get('source_observation_id')!=entry['observation_id']
                    or row.get('seed')!=entry['identity']['seed'] or row.get('border_side')!=side
                    or row.get('layout_id') in seen):raise ValueError('Invalid projected summary source')
            seen.add(row['layout_id'])
            if not trusted:
                if v3:
                    from .codec import validate_summary_v3
                    validate_summary_v3(row,registry=value['registry'])
                else:
                    from .codec import validate_summary_v2
                    validate_summary_v2(row)
        return value['rows']

    def iter_query_summaries(self,manifest,side,mode):
        """Read only the requested border; old immutable snapshots use their bundles."""
        for entry in manifest['worlds']:
            rows=self._projection(entry,side,mode) if 'summary_artifacts' in entry else self._bundle(self.artifacts.get_json(entry['artifact']),entry)['summaries']
            for row in rows:
                if row['border_side']==side and mode in row['anchor_modes']:
                    # Current projections are exact views of fully validated writer
                    # input, bound by validator revision and the immutable CAS root.
                    yield row


## correction CLI
#!/usr/bin/env python3
"""Correct per-mode legacy bindings and compact derived views within the original budget."""
import argparse
import copy
import json
import os
from pathlib import Path
import resource
import sqlite3
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT))
from seed_search.catalog.store import AutomationStore
from seed_search.catalog.harvest import HarvestQueue
from seed_search.catalog import automation
from seed_search.catalog.registry import digest
from seed_search.catalog.ingestion import atomic_json,strict_json_loads,tree_bytes
from seed_search.catalog.retention import retain,objective_family
from scripts.reanchor_catalog import copy_history


def run(root,source,destination):
    root=Path(root).absolute();source=Path(source).absolute();destination=Path(destination).absolute()
    if len({root,source,destination})!=3 or any(a in b.parents for a in (root,source,destination) for b in (root,source,destination) if a!=b):raise ValueError('Disjoint roots required')
    started=time.monotonic();store=AutomationStore(root);legacy_store=AutomationStore(source)
    migration_path=root/'automation/biome-expansion-progress.json';migration=strict_json_loads(migration_path.read_bytes())
    if not migration['complete'] or migration['total_budget_seconds']!=3600:raise ValueError('Completed bounded migration required')
    path=root/'automation/biome-projection-progress.json'
    current=store.snapshot();legacy=legacy_store.snapshot();pin=digest([migration['publication'],digest(legacy),str(destination)])
    old_config=strict_json_loads((root/'automation/configuration.json').read_bytes())
    if path.exists():state=strict_json_loads(path.read_bytes())
    else:
        state=dict(revision='catalog-biome-correction-v1',pin=pin,consumed_seconds=migration['consumed_seconds'],worlds=[],complete=False)
        atomic_json(path,state)
    if state['pin']!=pin:raise ValueError('Correction input changed')
    if state['complete']:return state
    initial=state['consumed_seconds']
    resource.setrlimit(resource.RLIMIT_CPU,(max(1,int(3600-initial)+5),max(1,int(3600-initial)+10)))
    def spent():return initial+time.monotonic()-started
    def guard():
        if spent()>=3600 or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss>4<<30 or tree_bytes(root)+(tree_bytes(destination) if destination.exists() else 0)>2<<30:raise TimeoutError('Original migration budget/caps exhausted; no reset')
    guard()
    if not destination.exists():
        if 2*tree_bytes(root)+(100<<20)>2<<30:raise ValueError('Preserved history and correction output exceed preflight cap')
        state['consumed_seconds']=spent()+15;atomic_json(path,state)
        destination.mkdir();copy_history(root,destination)
        automation.configure(destination,old_config['identity'],old_config['options'],catalog_registry=current['registry'])
        automation.control(destination,'pause');state['consumed_seconds']=spent();atomic_json(path,state)
    target=AutomationStore(destination);config=automation.configuration(destination)
    originals={e['world_id']:e for e in legacy['worlds']};keep={e['world_id']:[] for e in current['worlds']}
    for member in current['memberships']:
        # The legacy families are rebuilt from every saved world's original grid.
        if member['objective_id'].startswith(('v2.','v3.','realm.','preset.','record.')):keep[member['world_id']].append(dict(objective_id=member['objective_id'],rank=member['rank'],member=member['member']))
    original_db=sqlite3.connect((root/'harvest.sqlite').as_uri()+'?mode=ro',uri=True)
    manifest=copy.deepcopy(current);manifest['policy_revision']=config['policy_revision'];manifest['worlds']=[]
    try:
        with HarvestQueue(destination) as queue,queue.supervisor() as acquired,queue.ownership():
            if not acquired:raise ValueError('Writer already active')
            ledger=automation._ledger(queue,config)
            for i,entry in enumerate(current['worlds']):
                if i<len(state['worlds']):
                    saved=state['worlds'][i]
                    if saved['entry']['world_id']!=entry['world_id'] or ledger.receipt(entry['world_id']) is None:raise ValueError('Correction cursor differs')
                    manifest['worlds'].append(saved['entry']);continue
                guard()
                if 3600-spent()<25:raise TimeoutError('Publication allowance unavailable')
                state['consumed_seconds']=spent()+8;atomic_json(path,state);begin=time.monotonic()
                old_entry=originals[entry['world_id']];rows=[];legacy_rows=[];changed=False
                for side in (2048,4096,8192):
                    original_rows=legacy_store._projection(old_entry,side)
                    by_mode={(tuple(r['anchor']),tuple(r['anchor_modes'])):r['legacy'] for r in original_rows}
                    for row in store._projection(entry,side):
                        value=by_mode[(tuple(row['anchor']),tuple(row['anchor_modes']))]
                        changed|=row['legacy']!=value;row['legacy']=value;rows.append(row)
                    legacy_rows.extend(r['legacy'] for r in original_rows if 'recommended' in r['anchor_modes'])
                updated=dict(entry)
                if changed:
                    bundle=store.artifacts.get_json(entry['artifact']);extension=store.artifacts.get_json(bundle['extension_artifact']) if bundle.get('extension_artifact') else None
                    updated['artifact']=target.stage(bundle['observation'],rows,extension=extension,registry_v3=current['registry'])
                refs={}
                for side in (2048,4096,8192):
                    chosen=[r for r in rows if r['border_side']==side]
                    value=dict(revision='catalog-query-projection-v5',registry=current['registry'],sampling_profile_revision=entry['sampling_profile_revision'],source_extension_id=entry['source_extension_id'],world_id=entry['world_id'],identity=entry['identity'],observation_id=entry['observation_id'],bundle_sha256=updated['artifact']['sha256'],summary_validator_sha256=target._query_validator_id(),row_count=len(chosen),border_side=side,rows=target._pack_query_rows(chosen,current['registry']))
                    refs[str(side)]=target.artifacts.put_json(value)
                updated['summary_artifacts']=refs
                selected=retain(legacy_rows,[entry['identity']]);grid={r['layout_id']:r for r in legacy_rows};offers=list(keep[entry['world_id']])
                for objective,members in selected['objectives'].items():
                    for member in members:
                        rank=list(member['rank'])
                        if member.get('layout_id') is not None:
                            layout=grid[member['layout_id']];rank[-1]=digest(['automation-anchor-v2',entry['world_id'],layout['anchor'],layout['border_side']])
                        if objective_family(objective) in ('profiles','diversity'):rank[0]=dict(decimal=rank[0])
                        offers.append(dict(objective_id=objective,rank=rank,member=dict(member,rank=rank,source_observation_id=entry['observation_id'])))
                evaluations,replay=original_db.execute('SELECT evaluations,replay FROM automation_receipts WHERE world_id=?',(entry['world_id'],)).fetchone()
                receipt=dict(world_id=entry['world_id'],identity=entry['identity'],observation_id=entry['observation_id'],artifact=updated['artifact'],evaluations=strict_json_loads(evaluations),replay=dict(strict_json_loads(replay),legacy_mode_binding_corrected=True))
                ledger.offer(receipt,offers);manifest['worlds'].append(updated)
                if time.monotonic()-begin>8:raise TimeoutError('Bounded correction world allowance exceeded')
                state['worlds'].append(dict(entry=updated,changed_legacy=changed));state['consumed_seconds']=spent();atomic_json(path,state)
                if (i+1)%25==0:print(json.dumps(dict(worlds=i+1,cumulative_seconds=spent())),flush=True)
            guard();state['consumed_seconds']=3600;atomic_json(path,state)
            manifest['memberships']=ledger.members();manifest['generation']=ledger.generation();target._manifest(manifest);sid=digest(manifest)
            artifact=target._write_manifest(manifest);binding=dict(revision='catalog-snapshot-binding-v2',snapshot_id=sid,generation=manifest['generation'],artifact=artifact)
            guard();atomic_json(target.generations_dir/(manifest['policy_revision']+'-'+str(manifest['generation'])+'.json'),binding)
            atomic_json(target.snapshots_dir/(sid+'.json'),binding);atomic_json(target.current_path,binding)
            guard();state.update(complete=True,snapshot_id=sid,consumed_seconds=spent(),bytes=tree_bytes(root)+tree_bytes(destination),corrected_worlds=sum(r['changed_legacy'] for r in state['worlds']));atomic_json(path,state)
            final=dict(migration,publication=sid,consumed_seconds=spent(),bytes=tree_bytes(destination),original_publication=migration['publication'],correction_root=str(destination),aggregate_output_bytes=state['bytes'])
            atomic_json(destination/'automation/biome-expansion-progress.json',final)
            print(json.dumps(dict(complete=True,snapshot_id=sid,cumulative_seconds=spent(),aggregate_output_bytes=state['bytes'],corrected_worlds=state['corrected_worlds'])),flush=True)
    finally:original_db.close()
    return state

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',required=True);p.add_argument('--source',required=True);p.add_argument('--destination',required=True);a=p.parse_args();run(a.root,a.source,a.destination)
