"""Selected, bounded actual BDS observations; provisional ground stays PARTIAL.

The runtime generates disposable worlds only. Neither sparse samples nor the
stable Script API's unavailable structure enumerator certify Realm eligibility.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import time
import threading
import tempfile
import uuid

import numpy as np

from .. import BACKEND_COMMIT
from ..seeds import parse_seed
from .raster import Raster
from .bounds import square, nether_square, native_bounds, contains

BUILD = '1.26.52.3'
IMAGE = 'bedrock-verification-poc:1.26.52.3'
IMAGE_ID = 'sha256:cf479afd0ab8a8bb095f7aa71fd42064cf5ba7aff6c8a8f4f5503aac826511d8'
ZIP_SHA256 = 'f6348d84fa714d04ca194f207e89453ca6bba0a1359396475271a52a150471c6'
REASONS = {'top', 'borderline', 'unusual', 'random_low_rank', 'explicit', 'manual'}
TOOLS = Path(__file__).with_name('bds_tools')
CLEANUP_GUARD = Path(tempfile.gettempdir())/'realm-pinned-bds-verifier.blocked.json'


def pinned_world_settings():
    """The tested server.properties values; seed is the separate request identity."""
    return {key:value for line in (TOOLS/'poc-server.properties').read_text().splitlines()
            if line and not line.startswith('#') and '=' in line
            for key,value in [line.split('=',1)] if key!='level-seed'}


def validate_bds_pins(cfg):
    """Reject settings the tested adapter cannot honor instead of ignoring them."""
    options = cfg.get('bds', cfg.get('verification',{}).get('bds',{}))
    allowed = {'enabled','version','docker_cli','image','image_id','cpus','memory_gib','verification_budget',
               'persist_snapshot','compare_reference','maximum_region_side','max_tiles_per_request',
               'max_cave_tiles','evidence_dir','world_settings'}
    if not isinstance(options,dict) or set(options)-allowed:
        raise ValueError('Unsupported BDS setting; generation/runtime overrides cannot be silently ignored')
    for key,expected in [('version',BUILD),('image',IMAGE),('image_id',IMAGE_ID),('cpus',4),('memory_gib',6),('maximum_region_side',256)]:
        value = options.get(key,expected)
        if isinstance(value,bool) or value!=expected:
            raise ValueError(f'BDS {key} must retain the tested pin {expected}')
    for key in ('enabled','persist_snapshot','compare_reference'):
        if key in options and not isinstance(options[key],bool):
            raise ValueError(f'BDS {key} must be boolean')
    for key,low,high in [('verification_budget',0,10000),('max_tiles_per_request',1,10000),('max_cave_tiles',1,10000)]:
        if key in options and (isinstance(options[key],bool) or not isinstance(options[key],int) or not low<=options[key]<=high):
            raise ValueError(f'BDS {key} must be an integer in {low}..{high}')
    for key in ('docker_cli','evidence_dir'):
        if key in options and (not isinstance(options[key],str) or not options[key].strip()):
            raise ValueError(f'BDS {key} requires a nonempty path string')
    game = cfg.get('game',{})
    if not isinstance(game,dict) or set(game)-{'edition','target_version','backend_model','backend_commit','bds_version','world_settings'}:
        raise ValueError('Unsupported verification game setting')
    for key,expected in [('edition','bedrock'),('target_version','26.52'),('backend_model','MC_26_50'),('backend_commit',BACKEND_COMMIT),('bds_version',BUILD)]:
        if key in game and game[key]!=expected:
            raise ValueError(f'Unpinned verification game setting {key}')
    settings = pinned_world_settings()
    for supplied in [cfg.get('world_settings'),game.get('world_settings'),options.get('world_settings')]:
        if supplied is not None and (not isinstance(supplied,dict) or any(key not in settings or value!=settings[key] for key,value in supplied.items())):
            raise ValueError('world_settings must match tested server.properties string values; unsupported overrides require a new validated runtime')
    return options


def tooling_identity():
    names = ('main.js', 'column_policy.js', 'fixture_policy.js', 'manifest.json', 'poc-server.properties', 'world_behavior_packs.json',
             'entrypoint.sh', 'probe_tools.py', 'poc_control.py', 'snapshot_reader.py', 'compare_saved_blocks.py')
    hashes = {name: hashlib.sha256((TOOLS/name).read_bytes()).hexdigest() for name in names}
    for name in ('verification.py','raster.py'):
        hashes[name] = hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
    return hashes


def tiles(bounds, spacing=4):
    """Cover one sampling lattice with <=256 squares, <=289 chunks each."""
    if len(bounds) != 4 or any(isinstance(v, bool) or not isinstance(v, int) for v in bounds):
        raise ValueError('Bounds must contain four integers')
    x0, z0, x1, z1 = bounds
    if x1 <= x0 or z1 <= z0 or isinstance(spacing, bool) or not isinstance(spacing, int) or not 1 <= spacing <= 256:
        raise ValueError('Nonempty half-open bounds and spacing 1..256 required')
    step = (256//spacing)*spacing
    for z in range(z0, z1, step):
        for x in range(x0, x1, step):
            side = max(spacing, min(step, x1-x), min(step, z1-z))
            yield {'id': f'tile_{x-x0}_{z-z0}', 'x0': x, 'z0': z, 'side': side,
                   'spacing': spacing, 'tileSize': side, 'batchSize': 16, 'method': 'native_top'}


SEMANTIC_POLICY = 'pinned_saved_palette_resolution_v1'
SEMANTIC_SOURCE = 'official BDS '+BUILD+' Script API 2.10.0 BlockPermutation.resolve'


def _exact_json(a,b):
    try:
        return json.dumps(a,sort_keys=True,allow_nan=False)==json.dumps(b,sort_keys=True,allow_nan=False)
    except (TypeError,ValueError):
        return False


def _supported_states(states):
    return (isinstance(states,dict) and all(isinstance(k,str) and isinstance(v,(str,int,bool)) for k,v in states.items()))


def _semantic_mismatch_inputs(mismatch):
    """Only supported state-only differences with independent type/overlay agreement."""
    probe=mismatch.get('probe',{});names=mismatch.get('savedLayers',[]);entries=mismatch.get('savedEntries',[])
    if (probe.get('waterEither') or not isinstance(probe.get('block'),str) or not names
        or names[0]!=probe['block'] or not entries or not all(isinstance(entry,dict) for entry in entries)
        or [entry.get('name') for entry in entries]!=names):
        return None,'Primary block identity mismatch or unavailable'
    if not isinstance(probe.get('waterlogged'),bool):
        return None,'API overlay flag unavailable'
    overlay=any(name in ('minecraft:water','minecraft:flowing_water') for name in names[1:])
    if overlay!=probe['waterlogged']:
        return None,'Overlay water mismatch'
    if not _supported_states(probe.get('states')) or not _supported_states(entries[0].get('states')) or entries[0].get('statesError'):
        return None,'API or saved permutation states unavailable/unsupported'
    return {'saved_palette':{'block':names[0],'states':entries[0]['states']},
            'expected_api':{'block':probe['block'],'states':probe['states']}},None


def _semantic_response_matches(inputs,response,source):
    return (source==SEMANTIC_SOURCE and isinstance(response,dict) and response.get('status')=='RESOLVED'
            and response.get('error') is None and _exact_json(response.get('requested'),inputs['saved_palette'])
            and _exact_json(response.get('resolved'),inputs['expected_api']))


def saved_blocks_consistent(saved):
    """Exact matches or individually revalidated pinned-runtime state proofs only."""
    if saved.get('unknownCount') or saved.get('unknown'):
        return False
    mismatches=saved.get('mismatches',[])
    if not mismatches:return True
    proof=saved.get('semantic_validation',{})
    identity=proof.get('identity',{})
    if (proof.get('policy')!=SEMANTIC_POLICY or proof.get('source')!=SEMANTIC_SOURCE
        or proof.get('same_container_restart') is not True or proof.get('snapshot_copied_before_restart') is not True
        or not isinstance(proof.get('container_name'),str) or not proof['container_name']
        or proof.get('restart_cleanup',{}).get('clean_shutdown') is not True
        or identity.get('bds_version')!=BUILD or identity.get('script_api')!='2.10.0'
        or identity.get('image_id')!=IMAGE_ID or identity.get('server_zip_sha256')!=ZIP_SHA256
        or identity.get('persist_snapshot') is not True or identity.get('tools_sha256')!=tooling_identity()):
        return False
    cases=proof.get('cases',[])
    if len(cases)!=len(mismatches):return False
    for i,(mismatch,case) in enumerate(zip(mismatches,cases)):
        inputs,_=_semantic_mismatch_inputs(mismatch)
        if (inputs is None or case.get('mismatch_index')!=i or case.get('status')!='RUNTIME_PROVEN'
            or not _exact_json(case.get('saved_palette'),inputs['saved_palette'])
            or not _exact_json(case.get('expected_api'),inputs['expected_api'])
            or not _semantic_response_matches(inputs,case.get('response'),case.get('response_source'))):
            return False
    return True


class VerificationAdapter:
    def __init__(self, cfg, store=None, *, runtime=None):
        self.cfg = cfg
        self.options = validate_bds_pins(cfg)
        self.store = store
        self.runtime = runtime
        self.used = 0
        self._reservation_lock = threading.Lock()
        self.cache = {}
        self.identity = {'edition': 'Bedrock', 'bds_version': BUILD, 'script_api': '2.10.0',
                         'image_id': IMAGE_ID, 'server_zip_sha256': ZIP_SHA256,
                         'runtime_allocation':{'cpus':4,'memory_gib':6,'published_ports':[]},
                         'world_settings':pinned_world_settings(),
                         'tools_sha256': tooling_identity(), 'persist_snapshot': bool(self.options.get('persist_snapshot', False)),
                         'compare_reference': bool(self.options.get('compare_reference', True))}

    def cache_identity(self):
        return self.identity

    def _reserve_attempt(self, budget):
        """Commit one unique attempt before extraction, across store connections.

        A crashed or interrupted reserved attempt remains consumed. Reservation
        never holds the database write lock during slow provider/BDS work.
        """
        if self.store is None:
            with self._reservation_lock:
                if self.used >= budget:
                    return None
                self.used += 1
                return self.used
        db = self.store.db
        if db.in_transaction:
            raise RuntimeError('Verification reservation requires no open caller transaction')
        with db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute("SELECT value FROM meta WHERE key='bds_verification_used'").fetchone()
            used = json.loads(row[0]) if row else 0
            if isinstance(used,bool) or not isinstance(used,int) or used<0:
                raise ValueError('Invalid persisted BDS verification attempt count')
            if used >= budget:
                return None
            attempt = used+1
            db.execute("INSERT INTO meta(key,value) VALUES ('bds_verification_used',?) "
                       "ON CONFLICT(key) DO UPDATE SET value=excluded.value",(str(attempt),))
        self.used = attempt
        return attempt

    def observation_id(self, seed, bounds, spacing=4):
        seed = str(parse_seed(seed))
        bounds = tuple(bounds)
        # Match verify's lattice validation without provider work or reservation.
        list(tiles(bounds,spacing))
        return hashlib.sha256(json.dumps([seed,bounds,spacing,self.identity],sort_keys=True).encode()).hexdigest()

    def get_cached(self, seed, bounds, spacing=4):
        key = self.observation_id(seed,bounds,spacing)
        return self.cache.get(key) or (self.store.get_observation(key) if self.store else None)

    def verify(self, seed, bounds, spacing=4, selection_reason='explicit', *, candidate_id=None, selection_probability=None, retry_failed=False):
        seed = str(parse_seed(seed))
        bounds = tuple(bounds)
        requests = list(tiles(bounds, spacing))
        if selection_reason not in REASONS:
            raise ValueError('Verification requires a documented selected-candidate reason')
        if selection_probability is not None and not 0 < selection_probability <= 1:
            raise ValueError('Selection probability must be in (0,1]')
        key = self.observation_id(seed,bounds,spacing)
        cached = self.cache.get(key) or (self.store.get_observation(key) if self.store else None)
        if cached and not (cached.get('status') == 'FAILED' and retry_failed):
            return cached
        if not self.options.get('enabled', True):
            return {'id': key, 'seed': seed, 'bounds': list(bounds), 'status': 'UNSUPPORTED', 'reason': 'BDS disabled'}
        budget = self.options.get('verification_budget', 20)
        if len(requests) > self.options.get('max_tiles_per_request', 16):
            return {'id': key, 'seed': seed, 'bounds': list(bounds), 'status': 'PARTIAL',
                    'reason': 'Footprint exceeds measured bounded tile policy; increase max_tiles_per_request explicitly', 'requested_tiles': len(requests)}
        attempt = self._reserve_attempt(budget)
        if attempt is None:
            return {'id': key, 'seed': seed, 'bounds': list(bounds), 'status': 'PARTIAL', 'reason': 'Verification budget exhausted'}
        start = time.monotonic()
        try:
            raw = (self.runtime or self._extract)(seed, requests)
            rows = raw.get('columns', [])
            raster = raster_from_columns(bounds, spacing, rows, raw)
            result = {'id': key, 'candidate_id': candidate_id, 'seed': seed, 'bounds': list(bounds),
                      'spacing': spacing, 'status': raster.quality(), 'selection_reason': selection_reason,
                      'selection_probability': selection_probability, 'identity': self.identity,
                      'elapsed_seconds': time.monotonic()-start, 'evidence': raw,
                      'raster': {'bounds': list(bounds), 'resolution': spacing,
                                 'height': [[float(v) if np.isfinite(v) else None for v in row] for row in raster.height],
                                 'known': raster.known.tolist(), 'water': raster.water.tolist(),
                                 'natural_ground': raster.natural_ground.tolist(), 'metadata': raster.metadata}}
            result['attempt'] = attempt
        except Exception as error:
            result = {'id':key, 'candidate_id':candidate_id, 'seed':seed, 'bounds':list(bounds),
                      'spacing':spacing, 'status':'FAILED', 'data_quality':'FAILED',
                      'seed_eligibility':'UNKNOWN', 'attempt':attempt, 'provider':'official BDS '+BUILD,
                      'identity':self.identity, 'selection_reason':selection_reason,
                      'selection_probability':selection_probability, 'elapsed_seconds':time.monotonic()-start,
                      'error':{'type':type(error).__name__, 'message':str(error)},
                      'reason':'Extraction failed; baseline and seed eligibility remain unchanged',
                      'retry_policy':'Cached failure returned until retry_failed=True; each retry consumes one verification attempt'}
            if self.store:
                attempt_record = {**result, 'id':key+':attempt:'+str(attempt), 'observation_id':key}
                self.store.upsert_observation(candidate_id, attempt_record)
        self.cache[key] = result
        if self.store:
            self.store.upsert_observation(candidate_id, result)
        return result

    @staticmethod
    def _canonical_surface_points(points):
        if not isinstance(points,(list,tuple)) or not points:
            raise ValueError('Surface verification requires 1..16 integral coordinate pairs')
        normalized=[]
        for point in points:
            if (not isinstance(point,(list,tuple)) or len(point)!=2
                or any(isinstance(v,bool) or not isinstance(v,int) for v in point)):
                raise ValueError('Surface points must contain integer x,z coordinates')
            normalized.append(tuple(point))
        canonical=tuple(sorted(set(normalized)))
        if len(canonical)>16:
            raise ValueError('Surface verification is bounded to 16 unique points')
        return canonical

    def observation_id_surface_points(self, seed, points):
        seed=str(parse_seed(seed))
        points=self._canonical_surface_points(points)
        return hashlib.sha256(json.dumps(['surface_points_v1',seed,points,self.identity],sort_keys=True).encode()).hexdigest()

    def get_cached_surface_points(self, seed, points):
        key=self.observation_id_surface_points(seed,points)
        return self.cache.get(key) or (self.store.get_observation(key) if self.store else None)

    def verify_surface_points(self, seed, points, selection_reason='explicit', *, candidate_id=None,
                              selection_probability=None, retry_failed=False):
        """One selected attempt in one world; observed point existence, never absence.

        Per-cell normalization deliberately avoids allocating the bounding box of
        distant points. Unknown/missing cells remain visible and a successful
        point request never certifies a Realm footprint or complete biome fit.
        """
        seed=str(parse_seed(seed))
        points=self._canonical_surface_points(points)
        if selection_reason not in REASONS:
            raise ValueError('Verification requires a documented selected-candidate reason')
        if selection_probability is not None and not 0 < selection_probability <= 1:
            raise ValueError('Selection probability must be in (0,1]')
        key=self.observation_id_surface_points(seed,points)
        cached=self.cache.get(key) or (self.store.get_observation(key) if self.store else None)
        if cached and not (cached.get('status')=='FAILED' and retry_failed):
            return cached
        base={'id':key,'operation':'surface_points_v1','candidate_id':candidate_id,'seed':seed,
              'requested_points':[list(point) for point in points], 'requested_point_count':len(points),
              'source':'actual','actual':False,'identity':self.identity,'provider':'official BDS '+BUILD,
              'existence_only':True,'absence_verified':False,'scope':'requested_surface_points_only',
              'selection_reason':selection_reason,'selection_probability':selection_probability,
              'surface_biome_observations':[],'surface_biome_expected_cells':len(points),
              'surface_biome_observed_cells':0,'surface_biome_missing_cells':len(points),
              'surface_biome_coverage_complete':False,'stable_sampled_observations':False}
        if not self.options.get('enabled',True):
            return {**base,'status':'UNSUPPORTED','reason':'BDS disabled'}
        if len(points)>self.options.get('max_tiles_per_request',16):
            return {**base,'status':'PARTIAL','reason':'Point request exceeds configured bounded tile policy'}
        attempt=self._reserve_attempt(self.options.get('verification_budget',20))
        if attempt is None:
            return {**base,'status':'PARTIAL','reason':'Verification budget exhausted'}
        requests=[{'id':'surface_point_'+str(i),'x0':x,'z0':z,'side':1,'spacing':1,'method':'native_top'}
                  for i,(x,z) in enumerate(points)]
        start=time.monotonic()
        try:
            raw=(self.runtime or self._extract)(seed,requests)
            if raw.get('evidenceRole')=='controlled_fixture' or raw.get('evidence_role')=='controlled_fixture':
                raise ValueError('Controlled fixture mutations cannot supply natural surface observations')
            rows=raw.get('columns',[]);observations=[];cells=[];metadata=None
            for x,z in points:
                cell=raster_from_columns((x,z,x+1,z+1),1,rows,raw)
                metadata=cell.metadata
                observations.extend(metadata['surface_biome_observations'])
                height=cell.height[0,0]
                cells.append({'x':x,'z':z,'height':float(height) if np.isfinite(height) else None,
                              'known':bool(cell.known[0,0]),'water':bool(cell.water[0,0]),'natural_ground':False})
            observed=sum(sample['status']=='OBSERVED' for sample in observations)
            result={**base,'status':'PARTIAL','actual':True,'attempt':attempt,
                    'elapsed_seconds':time.monotonic()-start,'evidence':raw,'point_cells':cells,
                    'surface_biome_observations':observations,'surface_biome_observed_cells':observed,
                    'surface_biome_missing_cells':len(points)-observed,'surface_biome_coverage_complete':observed==len(points),
                    'stable_sampled_observations':bool(raw.get('stable',False)),
                    'surface_biome_evidence':metadata['surface_biome_evidence'],
                    'surface_biome_mapping_provenance':metadata['surface_biome_mapping_provenance'],
                    'surface_biome_query_policy':metadata['surface_biome_query_policy'],
                    'surface_biome_canopy_rule':metadata['surface_biome_canopy_rule'],
                    'reason':'Actual selected surface points establish observations only; no absence, full biome fit or terrain certification'}
        except Exception as error:
            result={**base,'status':'FAILED','data_quality':'FAILED','seed_eligibility':'UNKNOWN','attempt':attempt,
                    'elapsed_seconds':time.monotonic()-start,'error':{'type':type(error).__name__,'message':str(error)},
                    'reason':'Extraction failed; baseline and seed eligibility remain unchanged',
                    'retry_policy':'Cached failure returned until retry_failed=True; each retry consumes one verification attempt'}
            if self.store:
                self.store.upsert_observation(candidate_id,{**result,'id':key+':attempt:'+str(attempt),'observation_id':key})
        self.cache[key]=result
        if self.store:self.store.upsert_observation(candidate_id,result)
        return result

    def sample_raster(self, seed, bounds, resolution, **kwargs):
        result = self.verify(seed, bounds, resolution, kwargs.get('settings', {}).get('selection_reason', 'explicit'))
        if 'raster' not in result:
            shape = (math.ceil((bounds[3]-bounds[1])/resolution), math.ceil((bounds[2]-bounds[0])/resolution))
            return Raster(bounds, resolution, np.full(shape, np.nan), metadata={'unsupported': result['status']=='UNSUPPORTED', 'failed':result['status']=='FAILED', 'reason': result.get('reason')})
        return Raster(**result['raster'])

    def verify_candidate(self, candidate, bounds=None, **kwargs):
        sx, sz = candidate.get('evaluation_center',candidate['stronghold'])
        bounds = bounds or candidate.get('bounds', {}).get('overworld') or square((sx,sz), self.cfg.get('deployment', {}).get('overworld_side_blocks', 1536))
        if isinstance(bounds, dict):
            bounds = bounds['overworld']
        from .coastal import coastal_mode
        side=self.cfg.get('deployment',{}).get('overworld_side_blocks',1536)
        half=side//2
        if coastal_mode(self.cfg) and tuple(bounds) != (sx-half, sz-half, sx+half, sz+half):
            raise ValueError('Coastal candidate verification requires the configured center square')
        return self.verify(candidate['seed'], bounds, candidate_id=candidate.get('id'), **kwargs)

    def verify_final_nether(self, seed, stronghold, *, evidence=None):
        return final_nether_evidence(seed, stronghold, evidence, self.identity,
                                     side=self.cfg.get('deployment', {}).get('nether_side_blocks', 896),
                                     center_kind='world_origin' if self.cfg.get('screening_revision','').startswith('origin-fixed-2048') else 'stronghold')

    def sample_caves(self, seed, bounds, spacing=128, ys=(0,-16,-32,-48)):
        """Explicit manual coarse cave inventory, with no absence certification."""
        if not self.options.get('enabled', True):
            return {'observations':[], 'status':'UNSUPPORTED', 'actual':False, 'source':None, 'reason':'BDS disabled'}
        requests = [{**q, 'method':'cave_biomes', 'caveYs':list(ys)} for q in tiles(tuple(bounds), spacing)]
        if len(requests)>self.options.get('max_cave_tiles', 144):
            raise ValueError('Manual cave region exceeds configured tile budget')
        raw = (self.runtime or self._extract)(str(parse_seed(seed)), requests)
        x0,z0,x1,z1 = bounds
        observations = [v for row in raw.get('columns',[]) for v in row.get('caves',[])
                        if x0<=v['x']<x1 and z0<=v['z']<z1]
        return {'observations':observations, 'status':'PARTIAL', 'source':'official BDS '+BUILD,
                'actual':True, 'identity':self.identity, 'raw':raw,
                'complete':False, 'reason':'Sparse underground biome samples cannot verify absence'}

    def _extract(self, seed, requests):
        # Serialize the tested single-server allocation across processes too.
        import fcntl
        import tempfile
        lock_path = Path(tempfile.gettempdir())/'realm-pinned-bds-verifier.lock'
        with lock_path.open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if CLEANUP_GUARD.exists():
                from .bds_tools import poc_control as control
                previous = json.loads(CLEANUP_GUARD.read_text())
                control.DOCKER = previous['docker_cli']
                state = control.container_state(previous['name'])
                if not state.get('stopped') and not state.get('removed'):
                    raise RuntimeError('Previous BDS cleanup remains unresolved; see '+str(CLEANUP_GUARD))
                CLEANUP_GUARD.unlink()
            return self._extract_locked(seed, requests)

    def _confirm_saved_block_semantics(self,name,requests,saved,root,report,folder):
        from .bds_tools import probe_tools as p, poc_control as control
        proof={'policy':SEMANTIC_POLICY,'source':SEMANTIC_SOURCE,'identity':self.identity,
               'container_name':name,'same_container_restart':False,'snapshot_copied_before_restart':True,
               'snapshot_path':str(folder),'cases':[],'batches':[],'status':'PARTIAL','palette_limit':64}
        saved['semantic_validation']=proof
        palettes={}
        for i,mismatch in enumerate(saved.get('mismatches',[])):
            inputs,reason=_semantic_mismatch_inputs(mismatch)
            case={'mismatch_index':i,'status':'UNRESOLVED','reason':reason}
            if inputs:
                case.update(inputs)
                key=json.dumps(inputs['saved_palette'],sort_keys=True)
                if key in palettes or len(palettes)<64:palettes.setdefault(key,inputs['saved_palette'])
                else:case['reason']='Bounded semantic palette limit exceeded'
            proof['cases'].append(case)
        if not palettes:
            saved['unresolved_mismatches']=list(saved.get('mismatches',[]))
            saved['unresolved_mismatch_count']=len(saved['unresolved_mismatches'])
            saved['semantic_match_count']=0
            return
        console=None;primary_error=None;responses={}
        CLEANUP_GUARD.write_text(json.dumps({'name':name,'docker_cli':control.DOCKER,'status':'SEMANTIC_RESTART_ACTIVE_OR_UNRESOLVED'})+'\n')
        try:
            state=control.container_state(name)
            if not state.get('stopped') or state.get('exit_code')!=0:
                raise RuntimeError('Semantic confirmation requires same clean stopped container')
            console=p.Probe(name,name+'_semantic')
            proof['same_container_restart']=True
            proof['start_seconds']=console.start_seconds
            values=list(palettes.values())
            for i in range(0,len(values),8):
                batch=values[i:i+8]
                q={'id':'semantic_palette_'+str(i//8),'x0':requests[0]['x0'],'z0':requests[0]['z0'],
                   'side':1,'spacing':1,'permutations':batch}
                response=console.request('permutations_resolve',q,timeout=30)
                proof['batches'].append(response)
                results=response.get('results',[])
                if len(results)!=len(batch):
                    proof.setdefault('response_errors',[]).append('Resolver result count mismatch')
                    continue
                for requested,result in zip(batch,results):
                    key=json.dumps(requested,sort_keys=True)
                    responses[key]=(result,response.get('source'))
            for case in proof['cases']:
                if 'saved_palette' not in case or case.get('reason'):continue
                key=json.dumps(case['saved_palette'],sort_keys=True)
                response,source=responses.get(key,(None,None))
                case['response']=response;case['response_source']=source
                if _semantic_response_matches(case,response,source):
                    case['status']='RUNTIME_PROVEN';case['reason']=None
                else:case['reason']='Pinned runtime did not prove exact saved/API type and full state equivalence'
        except BaseException as error:
            primary_error=error;proof['error']={'type':type(error).__name__,'message':str(error)}
        finally:
            try:cleanup=control.cleanup_container(name,console)
            except BaseException as error:
                cleanup={'stopped':False,'removed':False,'clean_shutdown':False,'interrupted':isinstance(error,KeyboardInterrupt),
                         'error_type':type(error).__name__,'error':str(error)}
            proof['restart_cleanup']=cleanup
            if cleanup.get('stopped') or cleanup.get('removed'):
                try:CLEANUP_GUARD.unlink(missing_ok=True)
                except OSError as error:proof['guard_error']=str(error)
            else:
                try:CLEANUP_GUARD.write_text(json.dumps({'name':name,'docker_cli':control.DOCKER,'cleanup':cleanup})+'\n')
                except OSError as error:proof['guard_error']=str(error)
            saved['unresolved_mismatches']=[mismatch for mismatch,case in zip(saved.get('mismatches',[]),proof['cases'])
                                          if case['status']!='RUNTIME_PROVEN']
            saved['unresolved_mismatch_count']=len(saved['unresolved_mismatches'])
            saved['semantic_match_count']=sum(case['status']=='RUNTIME_PROVEN' for case in proof['cases'])
            if cleanup.get('clean_shutdown') and not saved['unresolved_mismatches']:proof['status']='PROVEN_ALL_STATE_MISMATCHES'
            try:(root/(name+'-results.json')).write_text(json.dumps(report,indent=2)+'\n')
            except OSError as error:
                if primary_error is None:primary_error=error
                else:primary_error.add_note('Persisting semantic restart diagnostics also failed: '+str(error))
        if primary_error is not None:raise primary_error
        if cleanup.get('termination',{}).get('type')=='SystemExit':raise SystemExit(cleanup['termination']['code'])
        if cleanup.get('interrupted'):raise KeyboardInterrupt('Interrupted during semantic restart cleanup')
        if not cleanup.get('clean_shutdown'):
            raise RuntimeError('Clean stopped semantic confirmation server not established')

    def _extract_locked(self, seed, requests):
        from .bds_tools import probe_tools as p, poc_control as control
        cli = self.options.get('docker_cli', control.DOCKER)
        control.DOCKER = cli
        image = self.options.get('image', IMAGE)
        observed = json.loads(control.docker('image', 'inspect', image, capture_output=True, text=True).stdout)[0]['Id']
        if observed != IMAGE_ID or self.options.get('image_id', IMAGE_ID) != IMAGE_ID:
            raise ValueError('BDS image identity differs from the tested pinned image')
        info = json.loads(control.docker('info', '--format', '{{json .}}', capture_output=True, text=True).stdout)
        cpus = self.options.get('cpus', 4)
        if cpus != 4 or cpus > info['NCPU'] or self.options.get('memory_gib', 6) != 6:
            raise ValueError('Tested runtime requires 4 CPUs and 6 GiB container memory')
        root = Path(self.options.get('evidence_dir', 'runs/realm-bds-evidence')).resolve()
        root.mkdir(parents=True, exist_ok=True)
        from .resources import disk_policy,disk_status
        # Bound retained host snapshots/evidence separately from the scanner's
        # workspace. The Docker writable world lives on another filesystem.
        estimate=max(1,len(requests))*(1 << 30)
        report_disk=disk_status(root,disk_policy({}),additional_bytes=estimate)
        vm_text=control.docker('run','--rm','--entrypoint','/bin/df',image,'-Pk','/srv/bds',capture_output=True,text=True,timeout=30).stdout
        try:vm_free=int(vm_text.splitlines()[-1].split()[3])*1024
        except (ValueError,IndexError) as exc:raise RuntimeError('BDS Docker disk monitoring unavailable; generation not started') from exc
        if vm_free<(16 << 30)+estimate:raise RuntimeError('BDS Docker free-space reserve reached; generation not started')
        p.ROOT = control.ROOT = root
        p.IMAGE = image
        name = 'realm-bds-'+uuid.uuid4().hex[:12]
        report = {'name': name, 'seed': seed, 'tiles': [], 'columns': [], 'status': 'PARTIAL',
                  'disk_preflight':{'host':report_disk,'docker_free_bytes':vm_free,'request_growth_reservation_bytes':estimate}}
        console = None
        primary_error = None
        CLEANUP_GUARD.write_text(json.dumps({'name':name,'docker_cli':control.DOCKER,'status':'ACTIVE_OR_UNRESOLVED'})+'\n')
        try:
            p.create(name, seed, cpus)
            console = p.Probe(name, name)
            report['start_seconds'] = console.start_seconds
            for q in requests:
                disk_status(root,disk_policy({}),additional_bytes=estimate)
                tile = {'request': q, 'load': console.request('load', q)}
                if not tile['load']['fullyLoaded']:
                    raise RuntimeError('Requested tile not fully loaded')
                scan = {**q, 'id': q['id']+'_scan', 'method': q['method'] if q['method']=='cave_biomes' else ('compare' if self.identity['compare_reference'] else 'native_top'), 'compareMethod': 'native_top'}
                tile['scan'] = console.request('scan', scan)
                rows = console.rows(scan)
                if tile['scan']['missing'] or tile['scan']['mismatches']:
                    raise RuntimeError('Missing columns or within-tick reference mismatch')
                norm = lambda values: [{k:v for k,v in row.items() if k!='id'} for row in values]
                tile['stability'] = []
                stable = False
                for i in range(4):
                    time.sleep(1)
                    check = {**q, 'id': q['id']+'_stable_'+str(i)}
                    summary = console.request('scan', check)
                    current = console.rows(check)
                    changes = sum(a != b for a,b in zip(norm(rows), norm(current)))
                    tile['stability'].append({'changed_columns': changes, 'scan': summary})
                    rows = current
                    if changes == 0 and i >= 1:
                        stable = True
                        break
                tile['stable'] = stable
                if self.identity['persist_snapshot']:
                    tile['markers'] = console.request('dirty', q)
                    tile['sky'] = console.request('check_sky', q)
                    if tile['markers']['failed'] or tile['sky']['nonAir']:
                        raise RuntimeError('Sky marker restoration audit failed')
                report['columns'].extend(rows)
                report['tiles'].append(tile)
            report['save_seconds'] = console.save()
            report['resources'] = console.resources()
        except BaseException as error:
            primary_error = error
            report['status'] = 'FAILED'
            report['error'] = str(error)
            report['error_type'] = type(error).__name__
        finally:
            try:
                cleanup = control.cleanup_container(name,console)
            except BaseException as cleanup_error:
                cleanup = {'stopped':False,'removed':False,'clean_shutdown':False,
                           'interrupted':isinstance(cleanup_error,KeyboardInterrupt),
                           'error_type':type(cleanup_error).__name__,'error':str(cleanup_error)}
            report['cleanup'] = cleanup
            report['exit_code'] = cleanup.get('exit_code')
            if not cleanup.get('clean_shutdown'):
                report['status'] = 'FAILED'
                report['cleanup_failure'] = 'Clean stopped BDS state not established; snapshot forbidden'
            if cleanup.get('stopped') or cleanup.get('removed'):
                try:CLEANUP_GUARD.unlink(missing_ok=True)
                except OSError as error:report['guard_error'] = str(error)
            else:
                try:CLEANUP_GUARD.write_text(json.dumps({'name':name,'docker_cli':control.DOCKER,'cleanup':cleanup})+'\n')
                except OSError as error:report['guard_error'] = str(error)
            try:
                (root/(name+'-results.json')).write_text(json.dumps(report,indent=2)+'\n')
            except OSError as error:
                if primary_error is None:primary_error = error
                else:primary_error.add_note('Persisting cleanup diagnostics also failed: '+str(error))
        if primary_error is not None:
            raise primary_error
        if report['cleanup'].get('termination',{}).get('type')=='SystemExit':
            raise SystemExit(report['cleanup']['termination']['code'])
        if report['cleanup'].get('interrupted'):
            raise KeyboardInterrupt('Interrupted during BDS cleanup')
        if not report['cleanup'].get('clean_shutdown'):
            raise RuntimeError(report['cleanup_failure'])
        try:
            folder = p.snapshot(name, name+'-snapshot')
            report['coverage'] = p.coverage(folder, requests)
            if report['coverage']['seed'] != seed:
                raise RuntimeError('Saved-world signed seed differs')
            if self.identity['persist_snapshot'] and all(q['method']!='cave_biomes' for q in requests):
                columns = root/(name+'-columns.json')
                columns.write_text(json.dumps(report['columns']))
                output = control.docker('run','--rm','--entrypoint','/opt/reader/bin/python','--mount',f'type=bind,src={root},dst=/evidence,readonly','--mount',f'type=bind,src={TOOLS},dst=/tools,readonly',image,'/tools/compare_saved_blocks.py','/evidence/'+folder.name,'/evidence/'+columns.name,capture_output=True,text=True).stdout
                report['saved_blocks'] = json.loads(output)
                if report['saved_blocks'].get('mismatches'):
                    self._confirm_saved_block_semantics(name,requests,report['saved_blocks'],root,report,folder)
                report['complete_snapshot'] = all(r['presentChunks']==r['expectedChunks']==r['finalized'] for r in report['coverage']['regions'])
            report['stable'] = all(t['stable'] for t in report['tiles'])
            comparisons = report.get('saved_blocks', {})
            consistent = saved_blocks_consistent(comparisons)
            report['status'] = 'PASS' if report['stable'] and consistent and report.get('complete_snapshot') is not False else 'PARTIAL'
            (root/(name+'-results.json')).write_text(json.dumps(report, indent=2)+'\n')
            return report
        except BaseException as error:
            report['status'] = 'FAILED'
            report['error'] = str(error)
            report['error_type'] = type(error).__name__
            try:(root/(name+'-results.json')).write_text(json.dumps(report,indent=2)+'\n')
            except OSError as persistence_error:error.add_note('Persisting snapshot diagnostics also failed: '+str(persistence_error))
            raise



def raster_from_columns(bounds, spacing, columns, evidence):
    x0,z0,x1,z1 = bounds
    shape = (math.ceil((z1-z0)/spacing), math.ceil((x1-x0)/spacing))
    height = np.full(shape, np.nan)
    water = np.zeros(shape, dtype=bool)
    seen = {}
    water_known = np.ones(shape, dtype=bool)
    policy_counts = {}
    biome_samples = {}
    biome_source = "official BDS "+BUILD+" Script API 2.10.0 Dimension.getBiome"
    biome_query_policy = "one_cell_above_observed_exposed_support_or_water_including_snow_cover"
    biome_canopy_rule = "ignore_filtered_vegetation"
    for row in columns:
        x,z = row['x'],row['z']
        if not (x0<=x<x1 and z0<=z<z1) or (x-x0)%spacing or (z-z0)%spacing:
            continue
        if row.get('evidenceRole')=='controlled_fixture':
            raise ValueError('Controlled fixture mutations cannot supply natural-world rasters')
        key = (x,z)
        surface = row.get('surfaceBiome',{})
        sample = {'x':x,'z':z,'y':surface.get('y'),'name':surface.get('name'),
                  'status':surface.get('status','MISSING'),'source':surface.get('source',biome_source)}
        if sample['status']=='OBSERVED':
            if not isinstance(sample['name'],str) or not sample['name'].strip():sample['status']='INVALID_NAME'
            elif (sample['source']!=biome_source or surface.get('queryPolicy')!=biome_query_policy
                  or surface.get('canopyRule')!=biome_canopy_rule):sample['status']='INVALID_QUERY_POLICY'
            else:
                levels=[row.get('ground',{}).get('y'),row.get('waterTop')]+[c.get('y') for c in row.get('cover',[])]
                levels=[v for v in levels if isinstance(v,(int,np.integer)) and not isinstance(v,bool)]
                expected_y=max(levels)+1 if levels else None
                if (row.get('waterKnown') is not True or sample['y']!=expected_y
                    or isinstance(sample['y'],bool) or not isinstance(sample['y'],(int,np.integer))
                    or not -64<=sample['y']<=319):sample['status']='UNKNOWN_SURFACE'
        if key in biome_samples and biome_samples[key]!=sample:
            raise ValueError('Overlapping tile surface biome observations disagree')
        biome_samples[key]=sample
        value = (row.get('ground',{}).get('y'), row.get('waterDepth'), row.get('waterKnown'), row.get('policy'))
        if key in seen and seen[key] != value:
            raise ValueError('Overlapping tile observations disagree')
        seen[key] = value
        if 'error' not in row and value[0] is not None:
            index = ((z-z0)//spacing, (x-x0)//spacing)
            height[index] = value[0]
            valid_depth = isinstance(value[1],(int,np.integer)) and not isinstance(value[1],bool) and value[1]>=0
            water[index] = valid_depth and value[1]>0
            # Legacy columns did not inspect overlay liquid: retain observations,
            # but exclude them from certifiable geometry.
            water_known[index] = (row.get('policy')=='actual-column-v2' and row.get('waterKnown') is True
                                  and valid_depth)
            classification=row.get('ground',{}).get('classification','legacy_unclassified')
            policy_counts[classification]=policy_counts.get(classification,0)+1
    saved = evidence.get('saved_blocks', {})
    consistent = saved_blocks_consistent(saved)
    known = np.isfinite(height) & water_known
    if not evidence.get('stable', False) or not consistent or evidence.get('complete_snapshot') is False:
        known[:] = False
    biome_observations=[]
    for z in range(z0,z1,spacing):
        for x in range(x0,x1,spacing):
            sample=dict(biome_samples.get((x,z),{'x':x,'z':z,'y':None,'name':None,'status':'MISSING','source':biome_source}))
            if sample['status']=='OBSERVED' and not known[(z-z0)//spacing,(x-x0)//spacing]:sample['status']='UNSTABLE_OR_UNKNOWN_CELL'
            biome_observations.append(sample)
    biome_observed=sum(sample['status']=='OBSERVED' for sample in biome_observations)
    return Raster(bounds, spacing, height, known=known, water=water,
                  natural_ground=np.zeros(shape, dtype=bool), metadata={
                      'source':'actual', 'provider':'official BDS '+BUILD,
                      'water_evidence':'actual_blocks', 'water_policy':'actual-column-v2',
                      'surface_biome_observations':biome_observations,
                      'surface_biome_evidence':'actual_api_string_names',
                      'surface_biome_mapping_provenance':'unmapped_names_no_native_numeric_ids',
                      'surface_biome_expected_cells':height.size, 'surface_biome_observed_cells':biome_observed,
                      'surface_biome_missing_cells':height.size-biome_observed,
                      'surface_biome_coverage_complete':biome_observed==height.size,
                      'surface_biome_query_policy':biome_query_policy, 'surface_biome_canopy_rule':biome_canopy_rule,
                      'height_evidence':'observed_support_including_solid_snow_ice_cover',
                      'water_depth_units':'contiguous_block_cells_not_fractional_surface_height',
                      'water_unknown_cells':int(np.count_nonzero(np.isfinite(height) & ~water_known)),
                      'support_classification_counts':policy_counts,
                      'natural_ground_evidence':'observed_support_structure_provenance_unverified',
                      'coverage_complete':len(seen)==height.size, 'stable_sampled_observations':evidence.get('stable',False),
                      'limitations':['Structure provenance unavailable; cover can hide substrate; fractional fluid surface height unverified; new column policy awaiting pinned-runtime validation', 'Sparse sampling cannot certify unsampled connectivity']})


def final_nether_evidence(seed, stronghold, evidence=None, identity=None, *, side=896, center_kind='stronghold'):
    seed = str(parse_seed(seed))
    sx,sz = stronghold
    if any(isinstance(v,bool) or not isinstance(v,int) for v in stronghold):
        raise ValueError('Stronghold coordinates must be integers')
    exact_bounds = nether_square(stronghold, side)
    lo_x, lo_z, hi_x, hi_z = native_bounds(exact_bounds)
    bounds = [lo_x, lo_z, hi_x+1, hi_z+1]
    result = {'seed':seed, 'stronghold':list(stronghold) if center_kind=='stronghold' else None,
              'evaluation_center':list(stronghold),'center_kind':center_kind,'center':[sx/8,sz/8], 'bounds':bounds,
              'half_open':True, 'required':['fortress','bastion'], 'status':'PARTIAL', 'structures':{},
              'reason':'Stable Script API does not support exhaustive structure enumeration; import actual pinned-generation evidence'}
    if not evidence:
        return result
    if not isinstance(evidence.get('source'), str) or not evidence['source'].strip():
        raise ValueError('Imported Nether evidence requires a recorded source')
    if str(parse_seed(evidence.get('seed')))!=seed or evidence.get('bds_version')!=BUILD or evidence.get('dimension')!='nether':
        raise ValueError('Imported Nether evidence seed/build/dimension mismatch')
    exhaustive = evidence.get('coverage_complete') is True and evidence.get('exhaustive') is True and evidence.get('bounds')==bounds
    for kind in ('fortress','bastion'):
        anchors = []
        for row in evidence.get('structures',{}).get(kind,[]):
            if any(isinstance(row.get(k), bool) or not isinstance(row.get(k), int) for k in ('x','y','z')):
                raise ValueError('Imported Nether anchors require integer X/Y/Z block coordinates')
            if 'actual' in row and not isinstance(row['actual'], bool):
                raise ValueError('Imported anchor actual flag must be boolean')
            if 'source' in row and (not isinstance(row['source'], str) or not row['source'].strip()):
                raise ValueError('Imported anchor source must be a nonempty string')
            x,z = row['x'],row['z']
            if row.get('actual') is True and contains((x,z), exact_bounds):
                anchors.append(row)
        result['structures'][kind] = {'anchors':anchors, 'status':'VERIFIED' if anchors else ('ABSENT' if exhaustive else 'UNKNOWN')}
    statuses = [v['status'] for v in result['structures'].values()]
    result['status'] = 'VERIFIED' if all(s=='VERIFIED' for s in statuses) else ('FAILED' if 'ABSENT' in statuses else 'PARTIAL')
    result['evidence'] = evidence
    return result


def calibrate_prediction(predictor, observation, *, sea_level=63):
    """Compare only stable, known actual cells of the requested sampling lattice.

    Saved rasters supply the authoritative known mask. Raw-only calls require
    explicit bounds, resolution and stability; square tile overscan is excluded.
    """
    evidence = observation.get('evidence', observation)
    empty = lambda reason: {'sample_count':0, 'known_prediction_count':0, 'status':'UNSUPPORTED', 'reason':reason}
    if evidence.get('stable') is not True or evidence.get('status') in ('FAILED','CANCELLED','UNSUPPORTED') or observation.get('status') in ('FAILED','UNSUPPORTED'):
        return empty('Stable actual extraction evidence is required for calibration')
    saved = Raster(**observation['raster']) if 'raster' in observation else None
    bounds = observation.get('bounds', evidence.get('bounds', saved.bounds if saved else None))
    spacing = observation.get('spacing', observation.get('resolution', evidence.get('spacing', evidence.get('resolution', saved.resolution if saved else None))))
    if bounds is None or spacing is None:
        return empty('Requested half-open bounds and sampling resolution are required')
    if saved is not None:
        if tuple(bounds)!=saved.bounds or spacing!=saved.resolution:
            raise ValueError('Saved calibration raster differs from requested bounds or resolution')
        if saved.metadata.get('source')!='actual' or saved.metadata.get('water_evidence')!='actual_blocks' or saved.metadata.get('stable_sampled_observations') is not True or saved.water is None:
            return empty('Saved raster lacks stable actual height/water evidence')
    columns = evidence.get('columns')
    if columns is not None:
        # Unknown or malformed ground/water fields are not negative evidence.
        valid = [row for row in columns if 'error' not in row
                 and isinstance(row.get('ground',{}).get('y'),(int,np.integer))
                 and not isinstance(row['ground']['y'],bool)
                 and isinstance(row.get('waterDepth'),(int,np.integer))
                 and not isinstance(row['waterDepth'],bool) and row['waterDepth']>=0]
        raster = raster_from_columns(tuple(bounds), spacing, valid, evidence)
        if saved is not None:
            # Require agreement with the persisted authoritative raster, rather
            # than silently replacing saved unknown/conflicting cells.
            raster.known &= saved.known & (raster.height==saved.height) & (raster.water==saved.water)
    elif saved is not None:
        raster = saved
        comparisons = evidence.get('saved_blocks',{})
        if comparisons.get('mismatches') or comparisons.get('unknownCount') or evidence.get('complete_snapshot') is False:
            return empty('Saved block consistency or requested snapshot coverage is unresolved')
    else:
        return empty('No actual columns or saved actual raster supplied')
    mask = raster.known & np.isfinite(raster.height)
    if not mask.any():
        return empty('No stable known actual cells on the requested lattice')
    seed = observation.get('seed',evidence.get('seed'))
    if seed is not None and hasattr(predictor,'seed') and str(predictor.seed)!=str(seed):
        raise ValueError('Calibration predictor seed differs from actual observations')
    xx,zz = raster.coordinates()
    points = np.column_stack((xx[mask],zz[mask])).astype(np.int32)
    values = predictor.heights(points, 8)
    height = np.asarray(values[0] if isinstance(values,tuple) else values, dtype=float)
    count = len(points)
    if height.shape!=(count,):
        raise ValueError('Calibration predictor returned a different sample count')
    actual_height = raster.height[mask]
    actual_water = raster.water[mask]
    predicted_water = height<=sea_level
    known = np.isfinite(height)
    error = np.abs(height[known]-actual_height[known])
    return {'status':'SELECTED_SAMPLE_DIAGNOSTIC' if known.any() else 'PARTIAL',
            'sample_count':count, 'known_prediction_count':int(known.sum()),
            'excluded_actual_cell_count':int(raster.height.size-mask.sum()),
            'bounds':list(raster.bounds), 'spacing':int(raster.resolution),
            'height_mae_blocks':float(error.mean()) if len(error) else None,
            'height_max_absolute_error_blocks':float(error.max()) if len(error) else None,
            'height_mismatch_count':int((error>0).sum()),
            'water_proxy_mismatch_count':int((predicted_water[known]!=actual_water[known]).sum()),
            'land_proxy_mismatch_count':int((~predicted_water[known]!=~actual_water[known]).sum()),
            'actual_exposed_water_count':int(actual_water[known].sum()),
            'actual_exposed_water_sample_count':int(actual_water.sum()),
            'predicted_water_proxy_count':int(predicted_water[known].sum()),
            'count_policy':'Mismatch and water counts use paired finite predictions; sample count uses stable known actual cells',
            'predicted_water_evidence':'height_at_or_below_sea_level_proxy',
            'actual_water_evidence':'actual_exposed_water_blocks',
            'limitations':['Selected observations do not estimate population precision or recall',
                           'Sea-level proxy omits aquifers, inland water above sea level, waterlogging and ice',
                           'Actual ground is foliage-filtered; structure provenance unverified',
                           'Sparse land/water samples do not verify connectivity or formation closure']}
