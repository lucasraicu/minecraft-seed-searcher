"""Canonical template encoding of common historical and locked pending records.

Templates retain every field; only schema-fixed fragments are pre-encoded. All
variable values use the existing canonical encoder. Other paths use direct full
records. No JSON parse/encode round trip or alternate digest format is used.
"""
from dataclasses import dataclass
import copy
import re
import uuid
import os
import platform
import resource

from .native_records import build_record, observation, full_observation, NAMES

_TOKEN=object()
_STAGE_NAMES=('stronghold',*(f'structure_{n}' for n in NAMES[:10]),'final_nether_pair',
              'biome_palette_4y','ranking_inventory','structure_outpost')


@dataclass(frozen=True,init=False)
class _EncodedCandidate:
    id: str
    seed: str
    stronghold: tuple
    qualification: str
    encoding: str
    _token: object

    def __init__(self,*args,**kwargs):raise TypeError('Encoded rows are created by the validated native encoder')

    def get(self,key,default=None):
        if key=='inventory':return {}  # The exact blueprint pending schema has no legacy tasks.
        return getattr(self,key,default)

    def __getitem__(self,key):return getattr(self,key)


@dataclass(frozen=True,init=False)
class _EncodedResult:
    index: int
    seed: str
    anchors: tuple
    counts: tuple
    summary: str
    _token: object

    def __init__(self,*args,**kwargs):raise TypeError('Encoded rows are created by the validated native encoder')

    def get(self,key,default=None):
        if key=='counts':return dict(self.counts)
        return getattr(self,key,default)

    def __getitem__(self,key):return self.get(key)


def summary_encoding(result):
    if isinstance(result,_EncodedResult) and result._token is _TOKEN:return result.summary
    return None


def _owned(cls,*fields):
    result=object.__new__(cls)
    for name,value in zip(cls.__dataclass_fields__,(*fields,_TOKEN),strict=True):object.__setattr__(result,name,value)
    return result


def candidate_encoding(candidate, canonical):
    if isinstance(candidate,_EncodedCandidate) and candidate._token is _TOKEN:return candidate.encoding
    return canonical(candidate)


class PendingEncoder:
    """One configuration-local template; only count_mansion early failures fit."""
    def __init__(self, sample, canonical):
        self.canonical=canonical
        self.prefix=uuid.uuid4().hex
        while self.prefix in canonical(sample):self.prefix=uuid.uuid4().hex
        candidate=copy.deepcopy(sample)
        candidate['seed']=self.tag('seed');candidate['id']=self.tag('id');candidate['index']=self.tag('index')
        candidate['stronghold']=self.tag('point')
        candidate['bounds']['overworld']=self.tag('bounds');candidate['bounds']['final_nether']=self.tag('nether')
        candidate['final_nether_prediction']['bounds']=self.tag('nether')
        for name,o in candidate['required_structures'].items():
            if name=='mansion':candidate['required_structures'][name]=self.tag('mansion')
            else:
                o['bounds']=self.tag('bounds')
                if name=='stronghold':
                    for k in ('raw','coordinates','predicted_viable'):o[k]=self.tag('anchor')
        encoded=canonical(candidate).replace('%','%%')
        names=[]
        def hole(match):names.append(match[1]);return '%s'
        self.template=re.sub(r'"'+self.prefix+r':(seed|id|index|point|bounds|nether|mansion|anchor)"',hole,encoded)
        self.names=tuple(names)
        empty=full_observation('mansion',self.tag('bounds'),self.tag('raw'),[])
        empty.update(minimum_count=1,predicted_count=0,count_is_complete=True,floor_status='PENDING')
        self.empty_mansion=canonical(empty).replace(canonical(self.tag('bounds')),'%s').replace(canonical(self.tag('raw')),'%s')
        self.summary_templates={}

    def tag(self,name):return self.prefix+':'+name

    def encode_summary(self,native,index,seed,cfg,anchors,counts,rss):
        has_anchors=bool(native.nanchors)
        if has_anchors not in self.summary_templates:
            # Build a full reference shell only once per topology/configuration.
            shell=build_record(native,index,seed,cfg)
            shell.pop('anchors');shell['anchor_ids']=self.tag('ids')
            shell['index']=self.tag('index');shell['seed']=self.tag('seed');shell['total_seconds']=self.tag('seconds')
            shell['worker_cpu_seconds']=0.;shell['worker_pid']=os.getpid();shell['worker_peak_rss_bytes']=self.tag('rss')
            shell['discovery']['seed']=self.tag('seed')
            for key in ('coordinates','raw','predicted_viable'):shell['discovery']['stronghold'][key]=self.tag('points')
            shell['counts']=self.tag('counts')
            if hasattr(self,'prototype_metadata'):
                shell['prototype']=self.prototype_metadata
                shell['stage_seconds']=self.tag('stages')
            names=[]
            def hole(match):names.append(match[1]);return '%s'
            text=self.canonical(shell).replace('%','%%')
            template=re.sub(r'"'+self.prefix+r':(ids|index|seed|seconds|rss|points|counts|stages)"',hole,text)
            self.summary_templates[has_anchors]=(template,tuple(names))
        template,names=self.summary_templates[has_anchors]
        discovery='['+','.join(f'[{native.discovery.xz[2*j]},{native.discovery.xz[2*j+1]}]' for j in range(native.discovery.n))+']'
        values={'ids':'['+','.join('"'+a.id+'"' for a in anchors)+']','index':str(index),
                'seed':'"'+seed+'"','seconds':self.canonical(float(native.seconds)),
                'rss':str(rss),'points':discovery,'counts':self.canonical(counts)}
        if hasattr(self,'prototype_metadata'):values['stages']=self.canonical(_stage_times(native))
        return template%tuple(values[n] for n in names)

    def encode(self,c,index,seed):
        x,z=int(c.x),int(c.z);point=(x,z);cid=f'{seed}:{x}:{z}'
        bounds=[x-768,z-768,x+768,z+768]
        nb=[x/8-448,z/8-448,x/8+448,z/8+448];nb=[int(v) if int(v)==v else v for v in nb]
        # Never let a different native decision reuse this pending template.
        if c.count_missing!=1 or c.biome_evaluated or c.score or not c.observations[0].evaluated or not c.observations[0].full or any(c.observations[k].evaluated for k in range(1,13)):
            raise ValueError('Native result does not fit first-stage pending template')
        # Numeric values come from checked signed integers and exact eighths;
        # their JSON spelling is exactly canonical(), without per-scalar calls.
        point_json=f'[{x},{z}]';bounds_json='['+','.join(map(str,bounds))+']'
        o=c.observations[0]
        if not o.viable.n:
            raw='['+','.join(f'[{o.raw.xz[2*i]},{o.raw.xz[2*i+1]}]' for i in range(o.raw.n))+']'
            mansion_json=self.empty_mansion%(bounds_json,raw)
        else:
            mansion=observation(o,'mansion',bounds,1)
            if mansion['predicted_count']:raise ValueError('Unexpected Mansion eligibility')
            mansion_json=self.canonical(mansion)
        values={'seed':'"'+seed+'"','id':'"'+cid+'"','index':str(index),
                'point':point_json,'anchor':'['+point_json+']',
                'bounds':bounds_json,'nether':'['+','.join(map(str,nb))+']','mansion':mansion_json}
        encoded=self.template%tuple(values[n] for n in self.names)
        return _owned(_EncodedCandidate,cid,seed,point,'PENDING',encoded)


def fast_records(batch,start_index,store):
    """Own all strings before the native batch is freed; no borrowed C pointers."""
    from ..seeds import MASK64
    if batch.pointer is None:raise ValueError('Closed native batch')
    if batch.retention!='full':raise ValueError('Use retained_records for compact batches')
    if isinstance(start_index,bool) or not isinstance(start_index,int) or not 0<=start_index<=MASK64 or start_index+len(batch.seeds)>MASK64+1:
        raise ValueError('Invalid full64 index range')
    prototype=batch.prototype;cfg=prototype.cfg;result=[]
    from .config import dynamic_policy
    if dynamic_policy(cfg):return batch.records(start_index)
    if store._digest_version != 2 or batch.complete:return batch.records(start_index)
    if cfg.get('screening_revision'):return locked_records(batch,start_index,store)
    encoder=getattr(prototype,'_pending_encoder',None)
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if platform.system()=='Darwin' else 1024)
    for i,seed in enumerate(batch.seeds):
        native=batch.pointer.results[i];index=start_index+i
        if any(native.anchors[j].count_missing!=1 for j in range(native.nanchors)):
            result.append(build_record(native,index,seed,cfg));continue
        # A small result shell has the complete discovery/coverage schema. Avoid
        # allocating all deferred candidate dictionaries solely to encode them.
        if encoder is None and native.nanchors:
            sample=build_record(native,index,seed,cfg)
            encoder=PendingEncoder(sample['anchors'][0],store._canonical_candidate_reference)
            prototype._pending_encoder=encoder
        if encoder is None:
            result.append(build_record(native,index,seed,cfg));continue
        seed=str(seed)
        n=native.nanchors
        counts={'stronghold_anchors':n,'baseline_predicted':0,'baseline_pending':n,
                'confirmed_rejections':0,'unresolved_discovery':int(not n),'unresolved_stronghold_coverage':1}
        if n:counts.update(structure_stage_entered=n,checked_mansion=n,pending_mansion=n)
        anchors=tuple(encoder.encode(native.anchors[j],index,seed) for j in range(n))
        summary=encoder.encode_summary(native,index,seed,cfg,anchors,counts,rss)
        result.append(_owned(_EncodedResult,index,seed,anchors,tuple(counts.items()),summary))
    return result


class LockedPendingEncoder:
    """Bounded configuration-local canonical templates for early locked failures.

    The key includes every observation state/count and the native score. All
    coordinates remain variable. Mansion biome witnesses and palette evidence
    deliberately use the independent full builder. No evidence field is dropped.
    """
    encode_summary = PendingEncoder.encode_summary
    tag = PendingEncoder.tag
    limit = 256

    def __init__(self, cfg, canonical, synthetic):
        self.cfg=cfg;self.canonical=canonical;self.prefix=uuid.uuid4().hex
        self.summary_templates={};self.templates={}
        self.synthetic=synthetic
        self.prototype_metadata={'provider':'isolated_native_blueprint_batch','synthetic':synthetic,
            'evidence':'pinned predictor only; actual generation unverified',
            'stage_seconds_scope':'inclusive native evaluator wall time; no replay generation calls',
            'python_role':'record reconstruction and checkpoint persistence'}
        self.slots=tuple((NAMES.index(n),n) for n in cfg['search']['structure_order'])+((10,'fortress'),(11,'bastion'))

    def key(self,c):
        if not c.count_missing or c.biome_evaluated or c.observations[0].evaluated:return None
        state=[]
        for k,name in self.slots:
            o=c.observations[k]
            state.append((bool(o.evaluated),bool(o.full),int(o.viable.n if o.full else o.floor.n)))
        return (int(c.count_missing),int(c.score),tuple(state))

    def compile(self,key,sample,c):
        candidate=copy.deepcopy(sample)
        # A random marker must never alias an authored string.
        if self.prefix in self.canonical(sample):raise ValueError('Template marker collision')
        for field,tag in (('id','id'),('seed','seed'),('index','index'),('stronghold','point')):
            candidate[field]=self.tag(tag)
        candidate['bounds']['overworld']=self.tag('bounds')
        candidate['bounds']['final_nether']=self.tag('nether')
        candidate['final_nether_prediction']['bounds']=self.tag('nether')
        sh=candidate['required_structures']['stronghold'];sh['bounds']=self.tag('bounds')
        for field in ('raw','coordinates','predicted_viable'):sh[field]=self.tag('anchor')
        for k,name in self.slots:
            group='required_nether_structures' if k in (10,11) else 'required_structures'
            if name not in candidate[group]:continue
            o=candidate[group][name];o['bounds']=self.tag('nether' if k in (10,11) else 'bounds')
            if c.observations[k].evaluated:
                for field in ('coordinates','predicted_viable'):o[field]=self.tag(f'v{k}')
                if c.observations[k].full:o['raw']=self.tag(f'r{k}')
        names=[]
        def hole(match):names.append(match[1]);return '%s'
        template=re.sub(r'"'+self.prefix+r':([a-z0-9]+)"',hole,self.canonical(candidate).replace('%','%%'))
        counts={'structure_stage_entered':1,'baseline_pending':1}
        for k,name in self.slots:
            if k in (10,11):continue
            if c.observations[k].evaluated:
                counts['checked_'+name]=1
                if c.count_missing & (1<<k):counts['pending_'+name]=1
        if c.observations[10].evaluated:counts['nether_stage_entered']=1
        self.templates[key]=(template,tuple(names),counts)

    def encode(self,key,c,index,seed):
        x,z=int(c.x),int(c.z);h=self.cfg['deployment']['overworld_side_blocks']//2
        nh=self.cfg['deployment']['nether_side_blocks']//2
        nb=[x/8-nh,z/8-nh,x/8+nh,z/8+nh];nb=[int(v) if int(v)==v else v for v in nb]
        cid=f'{seed}:{x}:{z}';point=f'[{x},{z}]'
        values={'id':'"'+cid+'"','seed':'"'+seed+'"','index':str(index),'point':point,
                'anchor':'['+point+']','bounds':f'[{x-h},{z-h},{x+h},{z+h}]','nether':'['+','.join(map(str,nb))+']'}
        for k,name in self.slots:
            o=c.observations[k]
            if not o.evaluated:continue
            vectors=[(f'v{k}',o.viable if o.full else o.floor)]
            if o.full:vectors.append((f'r{k}',o.raw))
            for tag,points in vectors:
                values[tag]='['+','.join(f'[{points.xz[2*i]},{points.xz[2*i+1]}]' for i in range(points.n))+']'
        template,names,counts=self.templates[key]
        return _owned(_EncodedCandidate,cid,seed,(x,z),'PENDING',template%tuple(values[n] for n in names)),counts


def _stage_times(native):
    return {name:float(native.stage_seconds[k]) for k,name in enumerate(_STAGE_NAMES) if native.stage_seconds[k]}


def locked_records(batch,start_index,store):
    prototype=batch.prototype;cfg=prototype.cfg
    encoder=getattr(prototype,'_locked_pending_encoder',None)
    if encoder is None or encoder.synthetic!=batch.synthetic:
        encoder=LockedPendingEncoder(cfg,store._canonical_candidate_reference,batch.synthetic)
        prototype._locked_pending_encoder=encoder
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if platform.system()=='Darwin' else 1024)
    results=[]
    for i,seed in enumerate(batch.seeds):
        native=batch.pointer.results[i];index=start_index+i;seed=str(seed)
        keys=[encoder.key(native.anchors[j]) for j in range(native.nanchors)]
        missing=set(keys)-encoder.templates.keys()
        if any(k is None for k in keys) or len(encoder.templates)+len(missing)>encoder.limit:
            reference=build_record(native,index,seed,cfg)
            reference['prototype']=dict(encoder.prototype_metadata)
            reference['stage_seconds']=_stage_times(native)
            reference['total_seconds']+=float(native.seconds)
            results.append(reference);continue
        if missing:
            reference=build_record(native,index,seed,cfg)
            for j,key in enumerate(keys):
                if key not in encoder.templates:encoder.compile(key,reference['anchors'][j],native.anchors[j])
        n=int(native.nanchors)
        counts={'stronghold_anchors':n,'baseline_predicted':0,'baseline_pending':0,
                'confirmed_rejections':0,'unresolved_discovery':int(not n),'unresolved_stronghold_coverage':1}
        anchors=[]
        for j,key in enumerate(keys):
            anchor,part=encoder.encode(key,native.anchors[j],index,seed);anchors.append(anchor)
            for name,value in part.items():counts[name]=counts.get(name,0)+value
        summary=encoder.encode_summary(native,index,seed,cfg,anchors,counts,rss)
        results.append(_owned(_EncodedResult,index,seed,tuple(anchors),tuple(counts.items()),summary))
    return results
