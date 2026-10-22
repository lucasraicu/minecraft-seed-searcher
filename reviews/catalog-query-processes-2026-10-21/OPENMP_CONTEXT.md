READ-ONLY OpenMP restoration audit. User authorized bringing back existing OpenMP after approved catalog CPU process plan. No source change/build/job/server restart in this worker; review exact current build and dispatch. Codex independently audits runtime/build later. Existing personal60144 must remain; primary native bytesbeb32 unchanged; corrected serial isolated source-runtime binary19a4/source72694 from previous fixes. Do not infer compiled primary flags from source alone. Identify actual opt-in needs, native thread cap and oversubscription hazards, required bounded parity tests.

native/build.py
1: from pathlib import Path
2: import os
3: import platform
4: import sys
5: from cffi import FFI
6: 
7: ROOT = Path(__file__).resolve().parents[1]
8: sys.path.insert(0, str(ROOT/'src'))
9: from seed_search.realm.native_identity import native_source_fingerprint
10: ffibuilder = FFI()
11: header = (ROOT / "native/bridge.h").read_text()
12: ffibuilder.cdef("\n".join(line for line in header.splitlines() if not line.startswith("#")))
13: units = ["noise", "biomes", "layers", "biomenoise", "cave", "generator", "finders", "util", "quadbase", "mt"]
14: compile_args = ["-O3", "-std=c11", "-fwrapv", "-fno-inline-functions"]
15: compile_args += ['-DSS_SOURCE_FINGERPRINT="'+native_source_fingerprint()+'"']
16: include_dirs = [str(ROOT / "native"), str(ROOT / "vendor/cubiomes-bedrock")]
17: libraries = ["m"]
18: library_dirs, link_args = [], []
19: # Portable serial is the default. The opt-in runtime must be explicitly supplied;
20: # no machine-specific ISA is enabled by this build path.
21: prefix = os.environ.get("SEED_SEARCH_OPENMP_PREFIX")
22: if prefix:
23:     prefix = Path(prefix).resolve()
24:     if not (prefix / "include/omp.h").is_file():
25:         raise ValueError("OpenMP prefix needs include/omp.h")
26:     if platform.system() == "Darwin":
27:         # The local runtime is host-architecture only; do not silently link it to
28:         # Python's other universal2 slice. Serial builds retain universal2.
29:         required = "-arch " + platform.machine()
30:         if os.environ.get("ARCHFLAGS") != required:
31:             raise ValueError(f"OpenMP host build requires explicit ARCHFLAGS='{required}'")
32:         compile_args += ["-Xpreprocessor", "-fopenmp"]
33:     else:
34:         compile_args += ["-fopenmp"]
35:     include_dirs += [str(prefix / "include")]
36:     runtime=prefix/'lib'/('libomp.dylib' if platform.system()=='Darwin' else 'libomp.so')
37:     if not runtime.is_file():raise ValueError('OpenMP prefix needs its shared runtime library')
38:     compile_args += ['-DSS_OPENMP_LIBRARY="'+str(runtime)+'"']
39:     library_dirs += [str(prefix / "lib")]
40:     libraries += ["omp"]
41:     link_args += ["-Wl,-rpath," + str(prefix / "lib")]
42: ffibuilder.set_source(
43:     "seed_search._native", '#include "bridge.h"',
44:     sources=[str(ROOT / p) if __name__ == "__main__" else p for p in ["native/bridge.c"] + [f"vendor/cubiomes-bedrock/{u}.c" for u in units]],
45:     include_dirs=include_dirs,
46:     extra_compile_args=compile_args,
47:     libraries=libraries, library_dirs=library_dirs, extra_link_args=link_args,
48: )
49: if __name__ == "__main__":
50:     os.chdir(ROOT)
51:     (ROOT / "build").mkdir(exist_ok=True)
52:     # Match Python's extension loader; a macOS .dylib can otherwise leave an
53:     # older .abi3.so silently active after a successful standalone build.
54:     ffibuilder.compile(tmpdir="build", target=str(ROOT / "src/seed_search/_native.abi3.so"), verbose=True)

native/bridge.c
58:     setupGenerator(&ctx->overworld, MC_26_50, 0);
59:     setupGenerator(&ctx->nether, MC_26_50, 0);
60:     applySeed(&ctx->overworld, DIM_OVERWORLD, seed);
61:     applySeed(&ctx->nether, DIM_NETHER, seed);
62:     return ctx;
63: }
64: void ss_destroy(SeedContext *ctx) { free(ctx); }
65: int ss_openmp_enabled(void) {
66: #ifdef _OPENMP
67:     return 1;
68: #else
69:     return 0;
70: #endif
71: }
72: const char *ss_openmp_library(void) {
73: #ifdef SS_OPENMP_LIBRARY
74:     return SS_OPENMP_LIBRARY;
75: #else
76:     return NULL;
77: #endif
78: }
79: int ss_set_threads(SeedContext *ctx,int threads) {
80:     if(!ctx || threads<1 || threads>36 || (threads>1 && !ss_openmp_enabled()))return -1;
81:     ctx->threads=threads;
82:     return 0;
83: }
84: int ss_model(void) { return MC_26_50; }
85: const char *ss_model_name(void) { return mc2str(MC_26_50); }
86: const char *ss_biome_name(int id) {
87:     /* Pinned util.c omits these existing enum entries. */
88:     switch (id) {
89:         case small_end_islands: return "small_end_islands";
90:         case end_midlands: return "end_midlands";
91:         case end_highlands: return "end_highlands";
92:         case end_barrens: return "end_barrens";

native/blueprint_batch.inc
575:     if(p->max_buffer_bytes<allocated_bytes || p->max_buffer_bytes>((uint64_t)4<<30))return NULL;
576:     NBBatch *batch=calloc(1,sizeof(*batch));if(!batch)return NULL;
577:     batch->count=count;batch->results=calloc((size_t)count,sizeof(NBResult));
578:     if(!batch->results){free(batch);return NULL;}
579:     if(p->retention){batch->verdicts=calloc((size_t)count,sizeof(NBVerdict));if(!batch->verdicts){nb_free(batch);return NULL;}}
580:     int next=0;
581: #ifdef _OPENMP
582:     #pragma omp parallel num_threads(threads) if(threads>1)
583: #endif
584:     {
585: #ifdef _OPENMP
586:         #pragma omp single
587:         batch->effective_threads=omp_get_num_threads();
588: #else
589:         batch->effective_threads=1;
590: #endif
591:         NBWorker w={0};w.ctx=ss_create(0);w.p=p;w.allocated_bytes=&allocated_bytes;
592:         /* Atomic chunk claiming preserves dynamic load balancing without the
593:          * newer compiler's dispatch-deinit ABI absent in the pinned libomp. */
594:         while(1) {
595:             int first;
596: #ifdef _OPENMP
597:             #pragma omp atomic capture
598: #endif
599:             {first=next;next+=NB_WORK_CHUNK;}
600:             if(first>=count)break;
601:             int end=first+NB_WORK_CHUNK;if(end>count)end=count;
602:             for(int i=first;i<end;i++) {
603:                 w.fixture=fixtures?fixtures+i:NULL;
604:                 NB_PROFILE_BIND(&w,profiles,i);
605:                 NBResult *r=batch->results+i;r->input_offset=i;
606:                 r->error=nb_eval(&w,seeds[i],r);
607:                 if(p->retention && !r->error) {
608:                     NBVerdict *v=batch->verdicts+i;v->seed=seeds[i];v->anchors=(uint32_t)(p->origin?r->discovery.n:r->nanchors);
609:                     int kept=0,original=r->nanchors;
610:                     for(int j=0;j<original;j++) {

src/seed_search/realm/native_batch.py
55:     indices = np.arange(first, end, dtype=np.uint64)
56:     low = np.uint64(int(low32) & 0xFFFFFFFF)
57:     z = low | ((indices & np.uint64(0xFFFFFFFF)) << np.uint64(32))
58:     return z.astype(np.int64)
59: 
60: 
61: class Prototype:
62:     def __init__(self,directory,cfg):
63:         validate_config(cfg)
64:         if cfg.get('contract')!=BLUEPRINT_CONTRACT:raise ValueError('Prototype requires the exact blueprint contract')
65:         if not outpost_policy(cfg) and tuple(cfg['search']['structure_order'])!=(tuple(LOCKED_ORDER) if locked_policy(cfg) else NAMES[:10]):raise ValueError('Prototype requires its audited structure order')
66:         if cfg['search']['inventory_mode']!='eligibility':raise ValueError('Native baseline requires eligibility inventory mode; use the Python route for other profiles')
67:         if cfg['biomes']['spacing']!=64 or cfg['biomes']['lattice']!='world':raise ValueError('Prototype requires the world-aligned 64-block lattice')
68:         if directory is None:
69:             try:self.module=importlib.import_module('seed_search._blueprint_batch')
70:             except ImportError as exc:raise ValueError('Native blueprint extension unavailable; build native/blueprint_build.py or supply --native-build') from exc
71:             self.directory=None;path=Path(self.module.__file__).resolve()
72:             ffi,lib=self.module.ffi,self.module.lib
73:             runtime=ffi.string(lib.ss_openmp_library()).decode() if lib.ss_openmp_enabled() else None
74:             self.identity={'extension':str(path),'extension_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
75:                 'openmp':bool(lib.ss_openmp_enabled()),'runtime':runtime,
76:                 'runtime_sha256':hashlib.sha256(Path(runtime).read_bytes()).hexdigest() if runtime else None,
77:                 'scope':'packaged complete native blueprint baseline','production_extension_replaced':False,
78:                 'stronghold_after':int(lib.nb_stronghold_after()) if hasattr(lib,'nb_stronghold_after') else None}
79:         else:
80:             self.directory=Path(directory).resolve();self.identity=json.loads((self.directory/'identity.json').read_text())
81:             from .native_identity import validate_native_sources
82:             validate_native_sources(self.identity)

src/seed_search/realm/native_batch.py
195:                 raise ValueError('NumPy seed array must be C-contiguous')
196:             if buf.itemsize != 8:
197:                 raise TypeError('NumPy seed array must be int64 or uint64')
198:             dtype = getattr(seeds, 'dtype', None)
199:             if dtype is not None:
200:                 if dtype.name not in ('int64', 'uint64'):
201:                     raise TypeError('NumPy seed array must be int64 or uint64')
202:                 if dtype.byteorder not in ('=', '|', '<' if sys.byteorder == 'little' else '>'):
203:                     raise ValueError('NumPy seed array must have native byte order')
204:             if len(buf) != len(seeds) or buf.nbytes != len(seeds) * 8:
205:                 raise ValueError('NumPy seed array buffer length does not match seeds count')
206:         else:
207:             seeds=[parse_seed(s) for s in seeds]
208:         if max_misses is None:max_misses=self.cfg['search']['max_misses'] if retention=='survivors' and two_group_policy(self.cfg) else 0
209:         if not 1<=len(seeds)<=16384:raise ValueError('Native batches must contain 1–16,384 inputs')
210:         if isinstance(threads,bool) or not isinstance(threads,int) or not 1<=threads<=36:raise ValueError('Threads must be 1–36')
211:         if threads>1 and not self.identity['openmp']:raise ValueError('Parallel sweep needs an OpenMP private build')
212:         if not isinstance(complete,bool):raise ValueError('complete must be boolean')
213:         if retention not in ('full','survivors'):raise ValueError('Unknown retention mode')
214:         if isinstance(max_misses,bool) or not isinstance(max_misses,int) or not 0<=max_misses<=25:raise ValueError('max_misses must be 0–25')
215:         if retention=='full' and max_misses:raise ValueError('max_misses requires survivor retention')
216:         if retention=='survivors' and complete:raise ValueError('Compact retention and complete oracle sweep are separate paths')
217:         if fixture_masks is not None and (fixtures is None or len(fixture_masks)!=len(seeds) or any(isinstance(v,bool) or not isinstance(v,int) or not 0<=v<1<<29 for v in fixture_masks)):
218:             raise ValueError('Invalid synthetic missing masks')

src/seed_search/realm/native_batch.py
760:     """Production opt-in; unsupported profiles fail before any input publication."""
761:     validate_config(cfg)
762:     validate_sequence_range(start_index, count, cfg['search'].get('sequence', 'permutation'))
763:     if max_misses is None:max_misses=cfg['search']['max_misses'] if retention=='survivors' and two_group_policy(cfg) else 0
764:     if two_group_policy(cfg) and retention=='survivors' and max_misses!=cfg['search']['max_misses']:
765:         raise ValueError('V2 survivor budget must match the resolved config; set search.max_misses in the policy')
766:     if isinstance(count,bool) or not isinstance(count,int) or not 0<=count<=MASK64+1 or isinstance(start_index,bool) or not isinstance(start_index,int) or not 0<=start_index<=MASK64+1 or start_index+count>MASK64+1:raise ValueError('Invalid bounded full64 range')
767:     if count>100000 and not allow_prediction_scale:
768:         raise ValueError('Native ranges above 100,000 require explicit prediction scale')
769:     search=cfg['search']
770:     if search.get('numeric_threads_per_worker',1)!=1:raise ValueError('Numerical threads must equal one')
771:     if search.get('sequence')=='manifest':
772:         values=search.get('manifest_seeds')
773:         if (not isinstance(values,list) or not 1<=len(values)<=10000 or
774:             any(not isinstance(v,str) or str(parse_seed(v))!=v for v in values) or
775:             len(set(values))!=len(values) or start_index+count>len(values)):
776:             raise ValueError('Invalid or insufficient canonical full64 seed manifest')
777:     prototype=Prototype(native_build,cfg)
778:     if native_threads>1 and not prototype.identity['openmp']:raise ValueError('Native threads above one need an explicitly built OpenMP extension')
779:     ident=dict(identity or {'config':cfg,'count':count,'start_index':start_index,'backend':production_identity()})
780:     ident.update(execution='native',native=prototype.identity,
781:                  native_build=str(Path(native_build).resolve()) if native_build is not None else None,
782:                  evaluator='seed_search.realm.native_batch:run_native_scan')
783:     if top_k is None:top_k=search.get('top_k',0)
784:     if type(top_k) is not int or not 0<=top_k<=1000:raise ValueError('top_k must be an integer in 0–1000')
785:     harvest=None
786:     if catalog_root is not None:
787:         from ..catalog.bridge import prepare_campaign
788:         harvest=prepare_campaign(search,output,start_index,count,ident,catalog_root,sample_cap=catalog_sample_cap)
789:         ident['catalog_harvest']={k:harvest[k] for k in ('root','sample_cap','campaign_id')}
790:         print(json.dumps({'catalog_handoff':harvest}),file=sys.stderr,flush=True)
791:     result=persist_pipeline(prototype,output,count,run_key=search['run_key'],threads=native_threads,
792:         batch_size=native_batch_size,resume=resume,stop_after=stop_after,progress=progress,
793:         start_index=start_index,identity=ident,allow_prediction_scale=allow_prediction_scale,production=True,retention=retention,max_misses=max_misses,
794:         top_k=top_k)

src/seed_search/backend.py
14:               "desert_pyramid", "jungle_temple", "swamp_hut", "igloo", "ocean_ruin", "mansion",
15:               "buried_treasure", "trail_ruins", "abandoned_camp", "ruined_portal_nether", "end_city")
16: # Serializes wrapper access in a Python process; multiprocessing remains parallel.
17: _LOCK = threading.RLock()
18: # These pinned-version families use a uint32_t MT placement seed. Stronghold's
19: # village path, Mineshaft and Trial Chamber are deliberately excluded.
20: RAW_MT_TYPES=frozenset(('village','ancient_city','ruined_portal','shipwreck','monument','outpost','fortress','bastion'))
21: _RAW_LAYOUTS=OrderedDict()
22: _NATIVE_THREADS=1
23: 
24: def native_runtime():
25:     from .realm.native_identity import validate_compiled_sources
26:     validate_compiled_sources(ffi,lib)
27:     import hashlib
28:     from pathlib import Path
29:     ptr=lib.ss_openmp_library()
30:     path=Path(ffi.string(ptr).decode()) if ptr!=ffi.NULL else None
31:     return {'openmp':bool(lib.ss_openmp_enabled()),
32:             'runtime_sha256':hashlib.sha256(path.read_bytes()).hexdigest() if path else None,
33:             'policy':'outer-columns-static-min256-v1'}
34: 
35: def configure_native_threads(threads=1):
36:     """Set defaults for new handles; numerical-library thread limits stay separate."""
37:     global _NATIVE_THREADS
38:     if isinstance(threads,bool) or not isinstance(threads,int) or not 1<=threads<=36:
39:         raise ValueError('Native threads must be 1–36')
40:     with _LOCK:
41:         if threads>1 and not lib.ss_openmp_enabled():
42:             raise ValueError('Native threading requires an explicitly built OpenMP runtime')
43:         _NATIVE_THREADS=threads
44: 
45: 
46: def measure(operation,points=None):
47:     """Inclusive API timing; counters describe executed work, not eligibility."""
48:     def decorate(fn):
49:         @wraps(fn)
50:         def wrapped(self,*args,**kwargs):

