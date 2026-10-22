"""CPU-only contract/vector and wire-example checks; no GPU or production codec."""
from pathlib import Path
import json,sys,struct,hashlib,copy
R=Path(__file__).resolve().parents[2];E=Path(__file__).parent;sys.path.insert(0,str(R/'src'))
from seed_search.seeds import seed_from_index,seed_strided,MASK64
from seed_search.catalog.geometry import bounds_for,inside,distance2
from seed_search.catalog.registry import canonical_json,digest
from seed_search.backend import Backend
c=json.loads((R/'docs/gpu/gpu_contract_v1.json').read_text());v=json.loads((E/'CPU_REFERENCE_VECTORS.json').read_text());vectors=v['vectors'];count=0
assert c['status']=='defined-contract-only-no-gpu-implementation'
assert c['cpu_reference']['vectors_sha256']==hashlib.sha256((E/'CPU_REFERENCE_VECTORS.json').read_bytes()).hexdigest()
for row in vectors['full64']:assert str(seed_from_index(int(row['index']),int(row['run_key'])))==row['seed'];count+=1
for row in vectors['strided']:assert str(seed_strided(int(row['index']),int(row['low32'])))==row['seed'];count+=1
for row in vectors['signed_identity']:assert struct.pack('<Q',int(row['seed'])&MASK64).hex()==row['little_endian_u64_hex'];count+=1
for row in vectors['floor8']:assert row['overworld']//8==row['nether'];count+=1
for row in vectors['borders']:
 assert list(bounds_for(row['anchor'],row['side']))==row['bounds']
 for p in row['points']:assert inside(*p['point'],row['bounds'])==p['inside']and distance2(*p['point'],row['anchor'])==p['distance_squared']
 count+=1
for row in vectors['native_raw_village_attempts']:
 with Backend(row['seed'])as backend:position=backend.attempt('village',*row['region'])
 assert(list(position)if position else None)==row['position'];count+=1
f=c['transport']['frame'];prefix=struct.Struct(f['prefix_struct']);assert prefix.size==84
for section in c['transport']['sections'].values():assert struct.calcsize(section['record_struct'])==section['record_bytes']
inputs=b''.join(struct.pack('<QQII',i,0,3,0)for i in range(2));verdicts=b''.join(struct.pack('<QQBBHI',i,seed_from_index(i,2026101630)&MASK64,1,1,0,0)for i in range(2));payload=inputs+verdicts
header=dict(contract_digest=digest(c),operation='seed-map-full64',input_start='0',input_count=2,run_key='2026101630',sections={'inputs':dict(offset=0,count=2,record_bytes=24),'verdicts':dict(offset=len(inputs),count=2,record_bytes=24)})
header.update(run_id='cpu-contract-fixture',batch_id='0',cpu_build_id=c['cpu_reference']['native_pin']['extension_sha256'],gpu_build_id=digest(['CPU-only-wire-example']),compiler_flags='CPU-reference-only',policy_id='CPU-fixture-no-adoption',registry_id=c['cpu_reference']['registry_revision'],provider_id=c['cpu_reference']['native_identity']['source_sha256'],profile_id='seed-map-only',sequence={'kind':'full64','run_key':'2026101630'},output_capacity=f['frame_max_bytes'],methods=[],height_profiles=[],input_selection_receipt=digest(['CPU-owned-example-selection',2]))

def frame(h,p):
 raw=canonical_json(h);return prefix.pack(b'SSGPUV1\0',len(raw),len(p),hashlib.sha256(raw).digest(),hashlib.sha256(p).digest())+raw+p

def verify(raw):
 assert prefix.size<=len(raw)<=f['frame_max_bytes']
 magic,hl,pl,hh,ph=prefix.unpack(raw[:prefix.size]);assert magic==b'SSGPUV1\0'and 0<hl<=f['header_max_bytes']
 assert len(raw)==prefix.size+hl+pl
 hraw=raw[prefix.size:prefix.size+hl];p=raw[prefix.size+hl:]
 assert hashlib.sha256(hraw).digest()==hh and hashlib.sha256(p).digest()==ph
 h=json.loads(hraw);assert canonical_json(h)==hraw and h['contract_digest']==digest(c)
 assert all(k in h for k in c['transport']['required_header_fields'])
 assert 0<=int(h['run_key'])<=MASK64
 n=h['input_count'];assert type(n)is int and 0<n<=c['transport']['max_inputs_per_frame']
 assert 0<=int(h['input_start'])and int(h['input_start'])+n<=2**64
 spans=[]
 for name,s in h['sections'].items():
  assert name in c['transport']['sections'];size=s['count']*s['record_bytes'];assert s['record_bytes']==c['transport']['sections'][name]['record_bytes']
  assert s['offset']>=0 and s['count']>=0 and s['offset']+size<=len(p);spans.append((s['offset'],s['offset']+size))
 spans.sort();assert all(a[1]<=b[0]for a,b in zip(spans,spans[1:]))
 a=h['sections']['inputs'];b=h['sections']['verdicts'];assert a['count']==b['count']==n
 seen=set()
 for i in range(n):
  index,seed,selection,reserved=struct.unpack_from('<QQII',p,a['offset']+i*24)
  output_index,output_seed,personal,public,error,complete=struct.unpack_from('<QQBBHI',p,b['offset']+i*24)
  assert index==int(h['input_start'])+i and index not in seen and reserved==0 and selection&~3==0
  seen.add(index);assert seed==0 and output_index==index and output_seed==seed_from_index(index,int(h['run_key']))&MASK64
  assert personal==(1 if selection&1 else 0)and public==(1 if selection&2 else 0)and error==complete==0
 return True
raw=frame(header,payload);assert verify(raw);rejected=0
bad=[];bad.append(raw[:-1]);bad.append(raw[:-1]+bytes([raw[-1]^1]))
h=copy.deepcopy(header);h['sections']['verdicts']['offset']=0;bad.append(frame(h,payload))
h=copy.deepcopy(header);h['contract_digest']='0'*64;bad.append(frame(h,payload))
h=copy.deepcopy(header);h['input_count']=16385;bad.append(frame(h,payload))
p=bytearray(payload);p[len(inputs)+17]=0;bad.append(frame(header,bytes(p)))
p=bytearray(payload);p[len(inputs)+8]^=1;bad.append(frame(header,bytes(p)))
for value in bad:
 try:verify(value)
 except(AssertionError,ValueError,KeyError,struct.error):rejected+=1
 else:raise AssertionError('Malformed example accepted')
(E/'GPU_CONTRACT_VERIFICATION.json').write_text(json.dumps(dict(status='PASS',cpu_vectors=count,wire_record_sizes_checked=True,valid_seed_mapping_frame_bytes=len(raw),malformed_examples_rejected=rejected,contract_digest=digest(c),gpu_implementation=False,scope='CPU reference/vector replay and illustrative seed-map wire decoder only;notGPUparity orproductiondecodercertification'),indent=2)+'\n');print('GPU contract CPU-only verification PASS')
