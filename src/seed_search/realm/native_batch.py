"""Explicit native blueprint execution with owned, bounded durable stages.

All discovery/filter/inventory calculations happen in C. Python prepares owned
records directly; the replay provider remains an independent oracle. Full retention
keeps every input and anchor. Compact retention is an explicit separate contract
that saves predicted survivors and configured near misses with range receipts.
"""
import hashlib
import importlib.util
import json
import statistics
import time
from pathlib import Path

import numpy as np

from seed_search.backend import biome_catalog, structure_type
from seed_search.realm.blueprint import PALETTE, evaluate_seed, evaluate_dynamic_seed
from seed_search.realm.biomes import canonical
from seed_search.realm.bounds import native_bounds
from seed_search.realm.config import BLUEPRINT_CONTRACT, validate_config, locked_policy, river_policy, LOCKED_ORDER, outpost_policy, origin_policy, two_group_policy, marine_baseline_policy, dynamic_policy, stronghold_after, baseline_requirements
from seed_search.realm.capabilities import identity as production_identity
from seed_search.realm.store import RealmStore
from seed_search.realm.native_records import build_record
from seed_search.seeds import MASK64, parse_seed, seed_from_index

NAMES=('mansion','jungle_temple','desert_pyramid','monument','ancient_city','village',
       'trial_chamber','ruined_portal','shipwreck','mineshaft','fortress','bastion','outpost')
METRICS={'biome_cache_hits','stage_seconds','native_work','worker_cpu_seconds','total_seconds','worker_pid',
         'worker_peak_rss_bytes','prototype'}


def semantic_record(value):
    return {k:v for k,v in value.items() if k not in METRICS}


class Prototype:
    def __init__(self,directory,cfg):
        validate_config(cfg)
        if cfg.get('contract')!=BLUEPRINT_CONTRACT:raise ValueError('Prototype requires the exact blueprint contract')
        if not outpost_policy(cfg) and tuple(cfg['search']['structure_order'])!=(tuple(LOCKED_ORDER) if locked_policy(cfg) else NAMES[:10]):raise ValueError('Prototype requires its audited structure order')
        if cfg['search']['inventory_mode']!='eligibility':raise ValueError('Native baseline requires eligibility inventory mode; use the Python route for other profiles')
        if cfg['biomes']['spacing']!=64 or cfg['biomes']['lattice']!='world':raise ValueError('Prototype requires the world-aligned 64-block lattice')
        if directory is None:
            try:self.module=importlib.import_module('seed_search._blueprint_batch')
            except ImportError as exc:raise ValueError('Native blueprint extension unavailable; build native/blueprint_build.py or supply --native-build') from exc
            self.directory=None;path=Path(self.module.__file__).resolve()
            ffi,lib=self.module.ffi,self.module.lib
            runtime=ffi.string(lib.ss_openmp_library()).decode() if lib.ss_openmp_enabled() else None
            self.identity={'extension':str(path),'extension_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                'openmp':bool(lib.ss_openmp_enabled()),'runtime':runtime,
                'runtime_sha256':hashlib.sha256(Path(runtime).read_bytes()).hexdigest() if runtime else None,
                'scope':'packaged complete native blueprint baseline','production_extension_replaced':False,
                'stronghold_after':int(lib.nb_stronghold_after()) if hasattr(lib,'nb_stronghold_after') else None}
        else:
            self.directory=Path(directory).resolve();self.identity=json.loads((self.directory/'identity.json').read_text())
            path=Path(self.identity['extension'])
            if not path.is_relative_to(self.directory) or hashlib.sha256(path.read_bytes()).hexdigest()!=self.identity['extension_sha256']:
                raise ValueError('Private extension identity mismatch')
            runtime=self.identity.get('runtime')
            if runtime and hashlib.sha256(Path(runtime).read_bytes()).hexdigest()!=self.identity.get('runtime_sha256'):
                raise ValueError('Native OpenMP runtime identity mismatch')
            spec=importlib.util.spec_from_file_location('_blueprint_batch',path)
            self.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.module)
        if two_group_policy(cfg) and not dynamic_policy(cfg) and self.identity.get('stronghold_after',2)!=stronghold_after(cfg):
            raise ValueError('Native Stronghold placement differs from the resolved policy')
        self.ffi,self.lib=self.module.ffi,self.module.lib;self.cfg=json.loads(json.dumps(cfg))
        self.policy=self.ffi.new('NBPolicy *')
        self.policy.max_buffer_bytes=256<<20
        if not hasattr(self.policy,'outpost_goal'):raise ValueError('Native blueprint ABI changed; rebuild the extension before using this adapter')
        if two_group_policy(cfg) and not all(hasattr(self.policy,n) for n in ('two_group','floors','flexible_mask')):
            raise ValueError('Two-group policy requires the rebuilt native hard-floor ABI')
        if marine_baseline_policy(cfg) and not hasattr(self.policy,'marine_baseline'):
            raise ValueError('Marine baseline policy requires a rebuilt native extension')
        if dynamic_policy(cfg) and not all(hasattr(self.policy,name) for name in ('dynamic','nether_ids','optional_types')):
            raise ValueError('Dynamic baseline requires a rebuilt native extension')
        self.policy.locked=int(locked_policy(cfg))
        self.policy.river=int(river_policy(cfg))
        self.policy.outpost_goal=cfg['structures']['minimum_counts']['outpost'] if outpost_policy(cfg) else 0
        if two_group_policy(cfg):
            self.policy.two_group=1
            self.policy.floors=[cfg['structures']['hard_floors'].get(n,0) for n in NAMES]
            self.policy.flexible_mask=sum(1<<NAMES.index(n) for n in
                (('trial_chamber','village','ruined_portal','mineshaft','ancient_city',
                  'desert_pyramid','jungle_temple','shipwreck') if dynamic_policy(cfg) else
                 ('mansion','trial_chamber','village','ruined_portal','mineshaft','ancient_city','fortress','bastion')))
        if dynamic_policy(cfg):
            self.policy.dynamic=1
            self.policy.density_weights=[cfg['search']['density_weights'][n] for n in
                ('village','trial_chamber','ancient_city','desert_pyramid','jungle_temple','outpost')]
        if hasattr(self.policy,'marine_baseline'):self.policy.marine_baseline=int(marine_baseline_policy(cfg))
        if origin_policy(cfg) and not hasattr(self.policy,'origin'):
            raise ValueError('Origin policy needs the rebuilt native ABI')
        if hasattr(self.policy,'origin'):self.policy.origin=int(origin_policy(cfg))
        if outpost_policy(cfg):self.policy.structure_order=[NAMES.index(n) for n in cfg['search']['structure_order']]
        self.policy.bastion_goal=cfg['structures']['nether_minimum_counts']['bastion']
        self.policy.overworld_half=cfg['deployment']['overworld_side_blocks']//2
        self.policy.nether_half=cfg['deployment']['nether_side_blocks']//2
        self.policy.nether_goal=cfg['structures']['nether_minimum_counts']['fortress']
        self.policy.discovery=native_bounds(cfg['discovery']['overworld_bounds'])
        self.policy.types=[structure_type(n) for n in NAMES]
        self.policy.goals=[cfg['structures']['minimum_counts'][n] for n in NAMES[:10]]
        self.policy.y=cfg['biomes']['sample_y_levels'];self.policy.spacing=64
        self.policy.batch_size=cfg['biomes']['gate_batch_size']
        catalog=biome_catalog();ids={row['name']:row['id'] for row in catalog}
        self.families=cfg['biomes']['required_families']
        for row in catalog:
            self.policy.biome_members[row['id']]=sum(1<<i for i,f in enumerate(self.families) if canonical(row['name']) in (PALETTE[f]|({'frozen_peaks'} if dynamic_policy(cfg) and f=='peaks' else set())))
            name=canonical(row['name'])
            if hasattr(self.policy,'bonus_biome_members'):
                self.policy.bonus_biome_members[row['id']]=(int(name=='cherry_grove')|
                    int(name in ('badlands','wooded_badlands','eroded_badlands'))<<1|
                    int(name=='mushroom_fields')<<2|
                    int(name=='pale_garden')<<3|
                    int(name=='mangrove_swamp')<<4|
                    int(name=='flower_forest')<<5|
                    int(name=='bamboo_jungle')<<6|
                    ((int(name=='warm_ocean')<<7|int(name=='ice_spikes')<<8|int(name in ('windswept_savanna','shattered_savanna'))<<9) if dynamic_policy(cfg) else 0))
        if dynamic_policy(cfg):self.policy.nether_ids=[ids[name] for name in cfg['biomes']['nether_required']]
        if dynamic_policy(cfg):self.policy.optional_types=[structure_type(n) for n in ('swamp_hut','igloo','trail_ruins','ocean_ruin','buried_treasure')]
        self.policy.dark_id=ids['dark_forest'];self.policy.pale_id=ids['pale_garden']
        self.policy.fixture_surface=[ids[n] for n in ('plains','desert','forest','taiga','jungle',
                                                     'swamp','snowy_plains','dark_forest','jagged_peaks','stony_shore')]
        self.policy.fixture_caves=[ids[n] for n in ('lush_caves','dripstone_caves','deep_dark')]
        self.identity={**self.identity,
            'record_adapter_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'record_sources_sha256':{name:hashlib.sha256((Path(build_record.__code__.co_filename).parent/name).read_bytes()).hexdigest() for name in ('native_records.py','native_encoding.py')},
            'policy_sha256':hashlib.sha256(bytes(self.ffi.buffer(self.policy))).hexdigest(),
            'record_computation_identity':production_identity()}

    def sweep(self,seeds,threads=1,*,complete=False,fixtures=None,retention="full",max_misses=None,fixture_masks=None,fixture_deltas=None):
        seeds=[parse_seed(s) for s in seeds]
        if max_misses is None:max_misses=self.cfg['search']['max_misses'] if retention=='survivors' and two_group_policy(self.cfg) else 0
        if not 1<=len(seeds)<=16384:raise ValueError('Native batches must contain 1–16,384 inputs')
        if isinstance(threads,bool) or not isinstance(threads,int) or not 1<=threads<=36:raise ValueError('Threads must be 1–36')
        if threads>1 and not self.identity['openmp']:raise ValueError('Parallel sweep needs an OpenMP private build')
        if not isinstance(complete,bool):raise ValueError('complete must be boolean')
        if retention not in ('full','survivors'):raise ValueError('Unknown retention mode')
        if isinstance(max_misses,bool) or not isinstance(max_misses,int) or not 0<=max_misses<=25:raise ValueError('max_misses must be 0–25')
        if retention=='full' and max_misses:raise ValueError('max_misses requires survivor retention')
        if retention=='survivors' and complete:raise ValueError('Compact retention and complete oracle sweep are separate paths')
        if fixture_masks is not None and (fixtures is None or len(fixture_masks)!=len(seeds) or any(isinstance(v,bool) or not isinstance(v,int) or not 0<=v<1<<29 for v in fixture_masks)):
            raise ValueError('Invalid synthetic missing masks')
        if fixture_deltas is not None and (fixtures is None or len(fixture_deltas)!=len(seeds) or any(type(v) is not int or not 1<=v<=32 for v in fixture_deltas)):
            raise ValueError('Invalid synthetic deficit depths')
        # Independent call-local policy and buffers; shared adapters never mutate
        # a policy while CFFI releases the GIL for another call.
        policy=self.ffi.new('NBPolicy *');self.ffi.memmove(policy,self.policy,self.ffi.sizeof('NBPolicy'))
        policy.complete=int(complete);policy.retention=int(retention=='survivors');policy.max_misses=(self.cfg['search']['max_misses'] if two_group_policy(self.cfg) and retention=='full' else max_misses);values=self.ffi.new('uint64_t[]',[s&MASK64 for s in seeds])
        fixture_values=None
        if fixtures is not None:
            if len(fixtures)!=len(seeds):raise ValueError('One explicit fixture per input required')
            for x,z,missing in fixtures:
                if any(isinstance(v,bool) or not isinstance(v,int) for v in (x,z,missing)) or not -1000000<=x<=1000000 or not -1000000<=z<=1000000 or not -1<=missing<=(33 if dynamic_policy(self.cfg) else 28):
                    raise ValueError('Invalid synthetic fixture')
            fixture_values=self.ffi.new('NBFixture[]',[(*f, fixture_masks[i] if fixture_masks else 0,
                fixture_deltas[i] if fixture_deltas else 1) for i,f in enumerate(fixtures)])
        start=time.perf_counter()
        pointer=(self.lib.nb_sweep(values,len(seeds),policy,threads) if fixtures is None else
                 self.lib.nb_fixture_sweep(values,fixture_values,len(seeds),policy,threads))
        native_seconds=time.perf_counter()-start
        if pointer==self.ffi.NULL:raise RuntimeError('Native batch allocation or policy error')
        batch=Batch(self,pointer,seeds,native_seconds,complete,fixtures is not None,retention,max_misses)
        try:
            if pointer.count!=len(seeds) or pointer.effective_threads!=threads:
                raise RuntimeError('Native batch count or CPU team differs from request')
            if pointer.error:raise RuntimeError(f'Native batch failed with code {pointer.error}; no range may be committed')
            for i in range(pointer.result_count):
                offset=pointer.results[i].input_offset
                if not 0<=offset<len(seeds) or pointer.results[i].seed!=(seeds[offset]&MASK64):raise RuntimeError('Native full64 input identity mismatch')
                if pointer.results[i].error:raise RuntimeError(f'Native input {i} failed with code {pointer.results[i].error}; no range may be committed')
            return batch
        except BaseException:
            batch.close();raise


class Batch:
    def __init__(self,prototype,pointer,seeds,seconds,complete,synthetic,retention="full",max_misses=0):
        self.prototype=prototype;self.pointer=pointer;self.seeds=seeds
        self.native_seconds=seconds;self.complete=complete;self.synthetic=synthetic
        self.retention=retention;self.max_misses=max_misses

    def __enter__(self):return self
    def __exit__(self,*args):self.close()
    def close(self):
        if self.pointer is not None:self.prototype.lib.nb_free(self.pointer);self.pointer=None

    def summary(self):
        if self.pointer is None:raise ValueError('Closed native batch')
        rows=[]
        for i in range(self.pointer.result_count):
            r=self.pointer.results[i];seed=self.seeds[r.input_offset]
            rows.append({'seed':str(seed),'anchors':[
                {'stronghold':[a.x,a.z],'count_missing':a.count_missing,
                 'biome_evaluated':bool(a.biome_evaluated),'biome_mask':a.biome_mask,
                 'biome_n':a.biome_n,'score':a.score,
                 'qualification':('PREDICTED' if not a.fatal_missing and a.stronghold_count>=1 and a.biome_mask==8191 and
                     int(a.count_missing & self.prototype.policy.flexible_mask).bit_count()<=self.prototype.cfg['search']['max_misses'] else 'PENDING') if two_group_policy(self.prototype.cfg) else
                     ('PREDICTED' if not a.count_missing and a.biome_mask==8191 else 'PENDING')}
                for a in [r.anchors[j] for j in range(r.nanchors)]]})
        return rows

    def records(self,start_index=0,*,adapter='direct'):
        if self.pointer is None:raise ValueError('Closed native batch')
        if isinstance(start_index,bool) or not isinstance(start_index,int) or not 0<=start_index<=MASK64 or start_index+len(self.seeds)>MASK64+1:
            raise ValueError('Invalid full64 index range')
        cfg=self.prototype.cfg;records=[]
        if adapter not in ('direct','replay'):raise ValueError('Unknown record adapter')
        if self.retention!='full':raise ValueError('Use retained_records for compact batches')
        for i,seed in enumerate(self.seeds):
            native=self.pointer.results[i]
            if dynamic_policy(cfg):
                if adapter=='direct':record=build_record(native,start_index+i,seed,cfg)
                else:
                    provider=ReplayProvider(native,self.prototype)
                    record=evaluate_dynamic_seed(start_index+i,seed,cfg,backend_factory=lambda _:provider)
                if len(record['anchors'])!=native.nanchors:raise RuntimeError('Dynamic center count parity failure')
                if native.nanchors:
                    a=record['anchors'][0];c=native.anchors[0]
                    if (a['evaluation_center']!=[c.x,c.z] or
                        a['baseline_score_observed']!=c.score or
                        a['biomes']['sample_count']!=c.biome_n or
                        a['qualification']!='PREDICTED'):
                        raise RuntimeError('Native dynamic center, palette, or score parity failure')
                stage_keys=['stronghold',*[f'structure_{n}' for n in NAMES[:10]],
                    'final_nether_pair','biome_palette_4y','dynamic_center_search','structure_outpost']
                record['stage_seconds']={key:float(native.stage_seconds[k])
                    for k,key in enumerate(stage_keys) if native.stage_seconds[k]}
                record['total_seconds']+=float(native.seconds)
                record['prototype']={'provider':'isolated_native_blueprint_batch',
                    'synthetic':self.synthetic,'evidence':'pinned predictor only; actual generation unverified',
                    'python_role':'record reconstruction and checkpoint persistence'}
                records.append(record)
                continue
            if adapter=='direct':record=build_record(native,start_index+i,seed,cfg)
            else:
                provider=ReplayProvider(native,self.prototype)
                record=evaluate_seed(start_index+i,seed,cfg,backend_factory=lambda _:provider,short_circuit=not self.complete)
            if len(record['anchors'])!=native.nanchors:raise RuntimeError('Native/reconstructed anchor count mismatch')
            for j,a in enumerate(record['anchors']):
                c=native.anchors[j]
                expected=(not c.fatal_missing and c.stronghold_count>=1 and c.biome_mask==8191 and
                          (int(c.count_missing & self.prototype.policy.flexible_mask).bit_count()<=cfg['search']['max_misses'])) if two_group_policy(cfg) else (not origin_policy(cfg) or c.stronghold_count>=1) and not c.count_missing and c.biome_mask==8191
                order=[10,11,*[NAMES.index(n) for n in cfg['search']['structure_order']]] if locked_policy(cfg) else range(12)
                pending=['count_'+NAMES[k] for k in order if c.count_missing&(1<<k)]
                if origin_policy(cfg) and c.stronghold_evaluated and c.stronghold_count<1:
                    pending.insert(sum(bool(c.count_missing&(1<<k)) for k in order[:2+stronghold_after(cfg)]),'count_stronghold')
                if c.biome_evaluated:pending+=['biome_'+f for k,f in enumerate(self.prototype.families) if not c.biome_mask&(1<<k)]
                if marine_baseline_policy(cfg):pending+=['count_'+NAMES[k] for k in (3,8) if c.count_missing&(1<<k)]
                if (a['qualification']=='PREDICTED')!=expected or a['pending_reasons']!=pending or a['baseline_score_observed']!=c.score:
                    raise RuntimeError('Native decision/count/biome/ranking parity failure')
                if c.biome_evaluated:
                    if a['biomes']['sample_count']!=c.biome_n:raise RuntimeError('Native biome stop position mismatch')
                    for k,f in enumerate(self.prototype.families):
                        index=c.first_witness[k]
                        if index>=0 and a['biomes']['witnesses'][f]['coordinate']!=[c.biome_xyz[index*3+t] for t in range(3)]:
                            raise RuntimeError('Native first biome witness mismatch')
            keys=['stronghold',*[f'structure_{n}' for n in NAMES[:10]],'final_nether_pair','biome_palette_4y','ranking_inventory','structure_outpost']
            record['stage_seconds']={key:float(native.stage_seconds[k]) for k,key in enumerate(keys) if native.stage_seconds[k]}
            record['total_seconds']+=float(native.seconds)
            record['prototype']={'provider':'isolated_native_blueprint_batch','synthetic':self.synthetic,
                'evidence':'pinned predictor only; actual generation unverified',
                'stage_seconds_scope':'inclusive native evaluator wall time; no replay generation calls',
                'python_role':'record reconstruction and checkpoint persistence'}
            records.append(record)
        return records

    def retained_records(self,start_index=0):
        if self.pointer is None:raise ValueError('Closed native batch')
        if self.retention!='survivors':raise ValueError('Expected compact batch')
        if isinstance(start_index,bool) or not isinstance(start_index,int) or not 0<=start_index<=MASK64 or start_index+len(self.seeds)>MASK64+1:
            raise ValueError('Invalid full64 range')
        records=[]
        for i in range(self.pointer.result_count):
            native=self.pointer.results[i];offset=native.input_offset
            cfg=self.prototype.cfg
            if two_group_policy(cfg):
                cfg=json.loads(json.dumps(cfg));cfg['search']['max_misses']=self.max_misses
            if dynamic_policy(cfg):
                provider=ReplayProvider(native,self.prototype)
                record=evaluate_dynamic_seed(start_index+offset,self.seeds[offset],cfg,
                    backend_factory=lambda _:provider)
                if len(record['anchors'])!=1 or record['anchors'][0]['baseline_score_observed']!=native.anchors[0].score:
                    raise RuntimeError('Native dynamic retained-record parity failure')
                stage_keys=['stronghold',*[f'structure_{n}' for n in NAMES[:10]],
                    'final_nether_pair','biome_palette_4y','dynamic_center_search','structure_outpost']
                record['stage_seconds']={key:float(native.stage_seconds[k])
                    for k,key in enumerate(stage_keys) if native.stage_seconds[k]}
                record['total_seconds']+=float(native.seconds)
            else:record=build_record(native,start_index+offset,self.seeds[offset],cfg)
            for j,a in enumerate(record['anchors']):
                c=native.anchors[j]
                misses=int(c.count_missing & self.prototype.policy.flexible_mask).bit_count() if two_group_policy(cfg) else int(c.count_missing).bit_count()+13-int(c.biome_mask).bit_count()
                if (not c.biome_evaluated or misses>self.max_misses or
                    (two_group_policy(cfg) and (c.fatal_missing or c.biome_mask!=8191)) or
                    (not two_group_policy(cfg) and misses!=len(a['pending_reasons'])) or
                    (origin_policy(cfg) and c.stronghold_count<1)):
                    raise RuntimeError('Native retention decision parity failure')
                a['retention']={'classification':'PREDICTED_SURVIVOR' if two_group_policy(cfg) or not misses else 'NEAR_MISS',
                    'unmet_requirements':misses,'allowed_unmet_requirements':self.max_misses,
                    'requirements_total':baseline_requirements(self.prototype.cfg),
                    'scope':('14 structure categories, 13 Overworld biome families and 5 Nether biome families; no terrain gate' if dynamic_policy(self.prototype.cfg) else f'{baseline_requirements(self.prototype.cfg)-13} structure-count and 13 biome-family predictor requirements; marine starts required, terrain unassessed' if marine_baseline_policy(self.prototype.cfg) else f'{baseline_requirements(self.prototype.cfg)-13} core structure-count and 13 biome-family requirements; marine deferred' if locked_policy(self.prototype.cfg) else '12 structure-count and 13 biome-family predictor requirements at this anchor')}
            if self.synthetic:record['prototype']={'synthetic':True,'provider':'explicit_native_retention_fixture','evidence':'synthetic provider fixture; not a natural-world discovery'}
            record['retention']={'mode':'survivors','max_misses':self.max_misses,
                                 'discarded_anchor_records_not_retained':True}
            records.append(record)
        return records

    def retention_receipt(self):
        if self.pointer is None or self.retention!='survivors':raise ValueError('Expected open compact batch')
        # C allocated this zero-initialized fixed-width buffer. Hashing visits no
        # per-input Python dictionaries and covers every input and decision.
        raw=self.prototype.ffi.buffer(self.pointer.verdicts,self.pointer.count*self.prototype.ffi.sizeof('NBVerdict'))
        digest=hashlib.sha256(raw).hexdigest()
        # Totals from retained records; full anchor count is summed in C below.
        return {'version':'native-retention-receipt-v1','inputs':self.pointer.count,
                'input_decisions_sha256':digest,'retained_inputs':self.pointer.result_count,
                'retained_anchors':int(self.pointer.retained_anchors),
                'discovered_anchors':int(self.pointer.discovered_anchors)}


class ReplayProvider:
    """Return only evidence already calculated by C; unknown queries fail closed."""
    def __init__(self,result,prototype):
        self.native_work={};self.discovery=self.points(result.discovery)
        self.dynamic_center=(int(result.anchors[0].x),int(result.anchors[0].z)) if dynamic_policy(prototype.cfg) and result.nanchors else None
        self.dynamic_no_anchor=bool(dynamic_policy(prototype.cfg) and not result.nanchors)
        self.queries={};self.ids={};self.nether_ids={};self.pairs={};self.igloo_basements=set()
        for j in range(result.nanchors):
            a=result.anchors[j];h=prototype.policy.overworld_half;nh=prototype.policy.nether_half
            bounds=(a.x-h,a.z-h,a.x+h-1,a.z+h-1)
            if dynamic_policy(prototype.cfg):
                from seed_search.realm.dynamic import nether_bounds
                bb=nether_bounds((a.x,a.z));nb=native_bounds(bb)
            else:
                nx=-((-a.x)//8);nz=-((-a.z)//8);nb=(nx-nh,nz-nh,nx+nh-1,nz+nh-1)
            for k,name in enumerate(NAMES):
                o=a.observations[k]
                if not o.evaluated:continue
                b=nb if k in (10,11) else bounds
                self.queries[(name,b)]={'raw':self.points(o.raw),'viable':self.points(o.viable),
                                       'floor':self.points(o.floor),'full':bool(o.full)}
                if name=='mansion':
                    for q,(x,z) in enumerate(self.points(o.viable)):self.ids[(x,63,z)]=int(o.mansion_ids[q])
            if a.observations[10].evaluated:
                self.pairs[nb]={n:(self.queries[(n,nb)]['raw'],self.queries[(n,nb)]['viable']) for n in ('fortress','bastion')}
            for q in range(a.biome_n):
                self.ids[tuple(int(a.biome_xyz[3*q+t]) for t in range(3))]=int(a.biome_ids[q])
            if dynamic_policy(prototype.cfg):
                for k,name in enumerate(('swamp_hut','igloo','trail_ruins','ocean_ruin','buried_treasure')):
                    o=a.optional[k]
                    self.queries[(name,bounds)]={'raw':self.points(o.raw),'viable':self.points(o.viable),'floor':[],'full':True}
                    if name=='igloo':self.igloo_basements.update(self.points(o.viable))
                for q in range(a.nether_biome_n):
                    self.nether_ids[tuple(int(a.nether_biome_xyz[3*q+t]) for t in range(3))]=int(a.nether_biome_ids[q])
        self.discovery_bounds=native_bounds(prototype.cfg['discovery']['overworld_bounds'])

    @staticmethod
    def points(points):return [(int(points.xz[2*i]),int(points.xz[2*i+1])) for i in range(points.n)]
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def structure_pair(self,name,bounds):
        if name=='stronghold':
            if tuple(bounds)!=self.discovery_bounds:raise RuntimeError('Uncomputed discovery bounds')
            return self.discovery,self.discovery
        q=self.queries[(name,tuple(bounds))]
        if not q['full']:raise RuntimeError('Complete inventory was not calculated in native code')
        return q['raw'],q['viable']
    def structure_count(self,name,bounds,minimum):
        q=self.queries[(name,tuple(bounds))]
        return q['floor']
    def igloo_basement(self,x,z):return (x,z) in self.igloo_basements
    def nether_structure_pairs(self,bounds):return self.pairs[tuple(bounds)]
    def biome_points(self,points,dimension=0):
        source=self.nether_ids if dimension==-1 else self.ids
        return np.array([source[tuple(map(int,p))] for p in points],dtype=np.int32)


def persist_scan(prototype,run,count,*,run_key=0,threads=18,batch_size=256,resume=False):
    """Bounded experimental scan using the complete existing RealmStore schema."""
    if isinstance(count,bool) or not isinstance(count,int) or not 1<=count<=100000:raise ValueError('Pilot count must be 1–100,000')
    if not 1<=batch_size<=16384:raise ValueError('Invalid native batch size')
    cfg=json.loads(json.dumps(prototype.cfg));cfg['search']['run_key']=str(run_key)
    identity={'config':cfg,'prototype':prototype.identity,'count':count,'evidence_schema':'realm-full-records-v1'}
    wall=time.perf_counter();native=decode=persist=0.;batches=0
    with RealmStore(run,identity=identity,resume=resume) as store:
        store.configure_range(0,count,batch_size);store.recover_assignments()
        while True:
            assigned=store.claim_range('native-prototype')
            if assigned is None:break
            start,end=assigned;seeds=[seed_from_index(i,run_key) for i in range(start,end)]
            with prototype.sweep(seeds,threads) as batch:
                native+=batch.native_seconds;t=time.perf_counter();records=batch.records(start)
                decode+=time.perf_counter()-t
            for i,record in enumerate(records):
                if record['seed']!=str(seeds[i]) or record['index']!=start+i:raise RuntimeError('Batch coverage identity mismatch')
            t=time.perf_counter();store.complete_range(start,end,records);persist+=time.perf_counter()-t;batches+=1
        status=store.status()
        if status['completed_seeds']!=count:raise RuntimeError('Incomplete persisted native pilot')
    seconds=time.perf_counter()-wall
    return {'count':count,'wall_seconds':seconds,'input_seeds_per_second':count/seconds,
            'native_seconds':native,'reconstruction_seconds':decode,'persistence_seconds':persist,
            'batches':batches,'threads':threads,'batch_size':batch_size,'status':status,
            'scope':'native baseline + complete Python evidence reconstruction + RealmStore FULL SQLite; no terrain/BDS',
            'resume_note':'A resumed completed pilot does not measure new-input throughput'}


def persist_pipeline(prototype,run,count,*,run_key=0,threads=30,batch_size=1024,
                     resume=False,encoded=True,max_prepared_bytes=256<<20,
                     stop_after=None,progress=None,start_index=0,identity=None,
                     allow_prediction_scale=False,production=False,inflight=3,retention="full",max_misses=0,
                     prepare_on_writer=False):
    """Bounded native producer, record preparer and connection-owning writer.

    CFFI releases the GIL during generation. Record preparation runs on its own thread; SQLite stays on
    the writer thread. No initialized OpenMP state is forked. Every outstanding
    batch has a native allocation cap. Exceptions close all buffers, stop new
    claims, and recover uncommitted leases. No fallback changes implementation.
    """
    from concurrent.futures import ThreadPoolExecutor
    from collections import deque,Counter
    from seed_search.realm.native_encoding import fast_records
    from seed_search.realm.runner import (_scan_lock,_numerical_threads,_scale_gate,
                                         _seed,_validate_batch_seeds,process_tree_resources)
    from seed_search.realm.resources import disk_policy,disk_status
    from seed_search.realm.config import memory_budget_gib
    if isinstance(count,bool) or not isinstance(count,int) or not 0<=count<=MASK64+1:
        raise ValueError('Invalid finite native pipeline count')
    if count>100000 and not (production and allow_prediction_scale):
        raise ValueError('Native ranges above 100,000 require explicit production prediction scale')
    if isinstance(batch_size,bool) or not isinstance(batch_size,int) or not 1<=batch_size<=16384:
        raise ValueError('Invalid native batch size')
    if isinstance(threads,bool) or not isinstance(threads,int) or not 1<=threads<=34:
        raise ValueError('Native pipeline reserves two of 36 CPU slots for preparation/writing')
    if isinstance(inflight,bool) or not isinstance(inflight,int) or not 2<=inflight<=3:
        raise ValueError('Pipeline supports two or three bounded in-flight batches')
    if isinstance(max_prepared_bytes,bool) or not isinstance(max_prepared_bytes,int) or max_prepared_bytes<1:
        raise ValueError('Invalid prepared byte budget')
    if type(prepare_on_writer) is not bool:raise ValueError('Invalid preparation scheduling mode')
    if isinstance(start_index,bool) or not isinstance(start_index,int) or not 0<=start_index<=MASK64+1 or start_index+count>MASK64+1:
        raise ValueError('Invalid full64 range')
    if stop_after is not None and (isinstance(stop_after,bool) or not isinstance(stop_after,int) or stop_after<0):
        raise ValueError('Invalid stop_after')
    if retention not in ('full','survivors'):raise ValueError('Unknown retention mode')
    if isinstance(max_misses,bool) or not isinstance(max_misses,int) or not 0<=max_misses<=25 or (retention=='full' and max_misses):raise ValueError('Invalid retention threshold')
    cfg=json.loads(json.dumps(prototype.cfg));cfg['search']['run_key']=str(run_key)
    identity=identity or {'config':cfg,'prototype':prototype.identity,'count':count,'start_index':start_index,
                         'evidence_schema':'realm-full-records-v1','adapter':'owned-native-pipeline-v1'}
    identity={**identity,'retention':{'mode':retention,'max_misses':max_misses}}
    if production:_scale_gate(cfg,run,count,allow_prediction_scale)
    limits=disk_policy(cfg['search'],retention=retention);_,ceiling,reserve=memory_budget_gib(cfg['search'])
    wall=time.perf_counter();cpu=time.process_time();service=Counter();latencies=deque(maxlen=4096);pending=deque()
    peak=0;batches=committed=dispatched=0;failure=None;interrupted=False;max_pending=0;max_payload=0
    pool=None;preparer=None;native_futures=set();last_monitor=0.;last_progress=0.
    def compute(first,end):
        before=time.perf_counter();seeds=[_seed(i,cfg['search']) for i in range(first,end)]
        seed_seconds=time.perf_counter()-before
        return prototype.sweep(seeds,threads,**({'retention':retention,'max_misses':max_misses} if retention=='survivors' else {})),seed_seconds
    def prepare(native_future,first,end,store):
        batch,seed_seconds=native_future.result()
        with batch:
            before=time.perf_counter()
            records=batch.retained_records(first) if retention=='survivors' else (
                fast_records(batch,first,store) if encoded and not origin_policy(cfg) else batch.records(first))
            record_seconds=time.perf_counter()-before
            if retention=='full':_validate_batch_seeds(first,end,records,cfg['search'])
            else:
                for record in records:_validate_batch_seeds(record['index'],record['index']+1,[record],cfg['search'])
            before=time.perf_counter();prepared=(store.prepare_retained_range(first,end,records,batch.retention_receipt()) if retention=='survivors' else store.prepare_range(first,end,records))
            prepare_seconds=time.perf_counter()-before
            owned_estimate=prepared.payload_bytes*2+sum(len(r)*64 for r in prepared.seed_rows+prepared.candidate_rows)
            if owned_estimate>max_prepared_bytes:
                raise RuntimeError('Prepared batch exceeds owned byte budget; retry with smaller batches')
            return prepared,{'seed_preparation_seconds':seed_seconds,'native_seconds':batch.native_seconds,
                             'record_seconds':record_seconds,'preparation_wall_seconds':prepare_seconds},owned_estimate
    def submit(store):
        nonlocal dispatched,max_pending
        budget=None if stop_after is None else stop_after-dispatched
        if budget is not None and budget<=0:return False
        assigned=store.claim_range('native-pipeline',max_seeds=batch_size if budget is None else min(batch_size,budget))
        if assigned is None:return False
        first,end=assigned
        attempt=store.db.execute('SELECT attempts FROM ranges WHERE start=?',(f'{first:020d}',)).fetchone()[0]
        native_future=pool.submit(compute,first,end);native_futures.add(native_future)
        future=None if prepare_on_writer else preparer.submit(prepare,native_future,first,end,store)
        pending.append((first,end,attempt,future,time.perf_counter(),native_future))
        dispatched+=end-first;max_pending=max(max_pending,len(pending));return True
    with _scan_lock(run),_numerical_threads(),RealmStore(run,identity=identity,resume=resume) as store:
        store.configure_range(start_index,start_index+count,batch_size);store.recover_assignments()
        disk_status(store.run,limits,remaining_seeds=count-store.status()['completed_seeds'])
        pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='native-blueprint')
        preparer=ThreadPoolExecutor(max_workers=1,thread_name_prefix='native-records')
        try:
            while len(pending)<inflight and submit(store):pass
            while pending:
                first,end,attempt,future,queued,native_future=pending.popleft()
                before=time.perf_counter()
                if future is None:
                    native_future.result()
                    service['queue_wait_seconds']+=time.perf_counter()-before
                    prepared,stage_times,owned_estimate=prepare(native_future,first,end,store)
                else:
                    prepared,stage_times,owned_estimate=future.result()
                    service['queue_wait_seconds']+=time.perf_counter()-before
                service.update(stage_times)
                max_payload=max(max_payload,owned_estimate)
                before=time.perf_counter()
                store.complete_prepared(prepared,lease=('native-pipeline',attempt),
                    capacity_check=lambda n:disk_status(store.run,limits,additional_bytes=n))
                service['writer_wall_seconds']+=time.perf_counter()-before
                service.update(store.last_range_timings)
                batches+=1;committed+=end-first;latencies.append(time.perf_counter()-queued)
                del prepared
                native_futures.discard(native_future)
                now=time.perf_counter()
                if now-last_monitor>=1:
                    resources=process_tree_resources() or {}
                    if not resources.get('available'):raise RuntimeError('Process-tree monitoring unavailable; checkpoint retained')
                    peak=max(peak,resources['rss_bytes']);last_monitor=now
                    if resources['rss_bytes']+reserve*(1<<30)>ceiling*(1<<30):
                        raise RuntimeError('Process-tree RSS plus reserve exceeded memory ceiling')
                if progress is not None and now-last_progress>=10:
                    progress(store.status());last_progress=now
                while len(pending)<inflight and submit(store):pass
        except KeyboardInterrupt:
            interrupted=True
        except BaseException as exc:
            failure=exc
        finally:
            before=time.perf_counter()
            # Running C calls are finite/capped and cannot be killed safely;
            # cancellation prevents queued starts, then closes every owned result.
            for first,end,attempt,future,queued,native_future in pending:
                if future is not None:future.cancel()
            for native_future in native_futures:native_future.cancel()
            pool.shutdown(wait=True,cancel_futures=True)
            preparer.shutdown(wait=True,cancel_futures=True)
            for native_future in native_futures:
                if not native_future.cancelled():
                    try:native_future.result()[0].close()
                    except BaseException:pass
            service['shutdown_seconds']=time.perf_counter()-before
            store.recover_assignments()
            store.set_state('native_pipeline',{'threads':threads,'cpu_slots':threads+2,'batch_size':batch_size,
                'max_outstanding_batches':max_pending,'max_prepared_owned_estimate_bytes':max_payload,
                'max_native_buffer_bytes_per_batch':int(prototype.policy.max_buffer_bytes),
                'max_prepared_bytes':max_prepared_bytes,'service_seconds':dict(service),'batches':batches,
                'prepare_on_writer':prepare_on_writer,
                'retention':retention,'max_misses':max_misses,'invocation_completed_seeds':committed,'interrupted':interrupted,
                'error':str(failure) if failure else None})
            status=store.status()
        if failure is not None:raise failure
    seconds=time.perf_counter()-wall
    return {'count':count,'newly_committed':committed,'wall_seconds':seconds,
            'input_seeds_per_second':committed/seconds,'process_cpu_seconds':time.process_time()-cpu,
            **dict(service),'batches':batches,'threads':threads,'batch_size':batch_size,
            'batch_latencies_seconds':list(latencies),'batch_latency_sample_scope':'last 4096 completed batches',
            'max_outstanding_batches':max_pending,
            'max_prepared_owned_estimate_bytes':max_payload,'peak_process_tree_rss_bytes':peak,
            'status':status,'interrupted':interrupted,'encoded':encoded,'retention':retention,'max_misses':max_misses,
            'scope':('complete baseline evidence and FULL SQLite' if retention=='full' else 'C-filtered survivor/near-miss evidence and FULL SQLite range checkpoints')+', startup/drain/close included; no terrain/BDS'}



def run_native_scan(cfg,output,count,start_index=0,resume=False,identity=None,*,native_build=None,
                    native_threads=16,native_batch_size=4096,stop_after=None,progress=None,
                    allow_prediction_scale=False,retention="full",max_misses=None):
    """Production opt-in; unsupported profiles fail before any input publication."""
    validate_config(cfg)
    if max_misses is None:max_misses=cfg['search']['max_misses'] if retention=='survivors' and two_group_policy(cfg) else 0
    if two_group_policy(cfg) and retention=='survivors' and max_misses!=cfg['search']['max_misses']:
        raise ValueError('V2 survivor budget must match the resolved config; set search.max_misses in the policy')
    if isinstance(count,bool) or not isinstance(count,int) or not 0<=count<=MASK64+1 or isinstance(start_index,bool) or not isinstance(start_index,int) or not 0<=start_index<=MASK64+1 or start_index+count>MASK64+1:raise ValueError('Invalid bounded full64 range')
    if count>100000 and not allow_prediction_scale:
        raise ValueError('Native ranges above 100,000 require explicit prediction scale')
    search=cfg['search']
    if search.get('numeric_threads_per_worker',1)!=1:raise ValueError('Numerical threads must equal one')
    if search.get('sequence')=='manifest':
        values=search.get('manifest_seeds')
        if (not isinstance(values,list) or not 1<=len(values)<=10000 or
            any(not isinstance(v,str) or str(parse_seed(v))!=v for v in values) or
            len(set(values))!=len(values) or start_index+count>len(values)):
            raise ValueError('Invalid or insufficient canonical full64 seed manifest')
    prototype=Prototype(native_build,cfg)
    if native_threads>1 and not prototype.identity['openmp']:raise ValueError('Native threads above one need an explicitly built OpenMP extension')
    ident=dict(identity or {'config':cfg,'count':count,'start_index':start_index,'backend':production_identity()})
    ident.update(execution='native',native=prototype.identity,
                 native_build=str(Path(native_build).resolve()) if native_build is not None else None,
                 evaluator='seed_search.realm.native_batch:run_native_scan')
    result=persist_pipeline(prototype,output,count,run_key=search['run_key'],threads=native_threads,
        batch_size=native_batch_size,resume=resume,stop_after=stop_after,progress=progress,
        start_index=start_index,identity=ident,allow_prediction_scale=allow_prediction_scale,production=True,retention=retention,max_misses=max_misses)
    status=result['status'];status['interrupted']=result['interrupted']
    status['execution']={'kind':'native','threads':native_threads,'batch_size':native_batch_size,
                         'newly_committed':result['newly_committed'],'wall_seconds':result['wall_seconds'],
                         'batch_latency_sample_scope':result['batch_latency_sample_scope'],
                         'batch_latency_p50_seconds':statistics.median(result['batch_latencies_seconds']) if result['batch_latencies_seconds'] else None,
                         'batch_latency_p95_seconds':sorted(result['batch_latencies_seconds'])[min(len(result['batch_latencies_seconds'])-1,int(.95*len(result['batch_latencies_seconds'])))] if result['batch_latencies_seconds'] else None,
                         'retention':retention,'max_misses':max_misses,
                         ('durably_persisted_inputs_per_second' if retention=='full' else 'checkpointed_scanned_inputs_per_second'):result['input_seeds_per_second']}
    return status
