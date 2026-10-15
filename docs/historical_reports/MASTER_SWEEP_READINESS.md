# Current Master implementation readiness

Target: **Bedrock 26.52 / BDS 1.26.52.3**, Stronghold-centered **2688 × 2688 Overworld** and exact **1024 × 1024 Nether** squares. Require Stronghold, Village, Trial Chamber, Ancient City, Mineshaft, at least two wooded families, and **both Fortress and Bastion**. Initial discovery remains half-open `[-2500,2500)` in both dimensions. V1/V2 are independent; caves are manual and score-neutral.

**Production sweep unstarted. Authoritative large-search readiness is false.** The implementation provides a prediction pipeline and recovery machinery; these do not certify actual world generation. The old 2304/928 readiness record applies only to its historical contract and source identity.

**Authorized implementation/benchmark delivery completed:** 623 tests passed, the sole million-input run and full candidate audit passed, supported diagnostics completed, and optional failures/deferred branches are recorded. The [evidence seal](runs/master-implementation-2026-10-10/readiness.json) is advisory; it grants no production launch or game-accuracy certification.

| Plan requirement | Current outcome | Evidence or next gate |
|---|---|---|
| A1 reference and identities | Implemented and verified | Frozen source/native manifest, 567 reference tests, strict native parity, supported serial ASan/UBSan |
| A2 Stronghold trace | Private expanded trace passed seven controls | MT active state/draw positions, float/double angles, negative floor conversions, sorted candidates and signed/high32 controls match installed starts; independent game trace still required |
| A2 positive recovery | Implemented; 14 focused tests passed | Exact seed/build/settings/bounds/start conventions, immutable proof, atomic new anchors and V1/V2 tasks, replay/rollback/concurrent merge, explicit pool revision and score recovery |
| A2 actual acquisition and recall | Open game-evidence gate | A nearest result or missing prediction cannot prove exhaustive absence; no supported exact-build exhaustive enumerator established |
| A2a Nether contact/access | Deferred optional diagnostic | Requires actual generated footprints/Y extents; physical contact is not required for eligibility |
| A3 natural V1/V2 controls | Open game-evidence gate | Complete independently labeled positive/negative formations and halos, natural structure exclusion, liquid/ice/cover interpretation and held-out calibration |
| A3a terrain attribution | Bounded diagnostic complete; causal correction unproved | 256 identical saved columns joined to retained actual block evidence; missing primary/overlay fluids and structure provenance stay unknown |
| B1/B2/B2a exact terrain reuse | Implemented and verified on bounded reference controls | Raw/public exact parity, negative cells, heights 1/8/16, land quart grouping, retained Python cross-call cache, complete fixed-anchor V1/V2 replay |
| B3 coast frontier C port | Deferred conditional optimization | Legacy coast path is not this schema-5 scheduler; no relevant end-to-end gain established |
| B4 approximate hard exits | Rejected as unproved eligibility | Approximate height remains a scheduling hint; no deleted seeds or actual-absence inference |
| B4a durable priority | Implemented and fault-tested; opt-in | Indexed rank/age queues, variant alternation, 3:1 fairness, retries and bounded center budgets; measured bounded trial slower, so rotation remains default |
| C1 OpenMP | Implemented and verified | All native counts 1–36 match; original process/thread grid and all nine factorizations of 36 measured; single-process terrain selected at 18 threads |
| C1 alternative schedules | Attempted; dynamic/guided deferred at load gate | Private alternatives require a runtime symbol unavailable in the retained compiler/runtime pair; static repeat controls pass and installed binary is unchanged |
| C1a memory/disk policy | Implemented and fault-tested | 25 GiB target / 30 GiB ceiling including one 8 GiB VM reserve; 128 GiB run cap / 16 GiB free reserve; fail-closed host/Docker checks and durable drain/resume |
| C1a simultaneous BDS throughput | Open production resource gate | Solo trials and budget reservation do not establish concurrent generation latency or useful throughput |
| C2 SIMD | Strict isolated AVX2 tested; shipping deferred | About 2.3% native gain without demonstrated end-to-end win; AVX-512 OS state unsupported on this host; no fast-math or ISA flag promoted |
| D0/D1/D2 raw layout selection | Adapter and durable checkpoints implemented; promotion gate failed | Whole-envelope counts and exact joint-center witnesses reject only 30/4096 layouts; approximately 63-hour native full32 projection, before ranking/checkpoint costs |
| D3 high32 handoff | Finite full64 handoff implemented and tested | Distinct siblings, submitted/completed state, same mandatory baseline; selected versus independent cohort did not establish useful yield per CPU-hour |
| E exact million benchmark | Completed and audited | Exactly one million distinct inputs in 96.14 minutes, 173.37/s, 34.55 GiB; 31,250 contiguous completed ranges and all 2,629,026 candidate Nether bounds passed |
| E final regression/readiness seal | Completed; advisory implementation delivery verified | 623 tests passed in 89.60s; fresh source/native/config/evidence hashes, full audit, private diagnostics and requirement record saved |
| Border-size question | Nine matched trials completed; current borders retained | 2688/1500/1200 medians 188.74/371.58/423.48 inputs/s, but predicted anchors/s 228.46/192.85/144.24; discovery/Nether and production config unchanged |

The selected solo settings are **30 baseline processes × 1 native thread**, and **one terrain process × 18 native threads**. The process/thread grid measured independent jobs; it does not add a multiprocessing terrain executor or certify a mixed BDS profile.

The measured host build loads LLVM OpenMP 17.0.6 from `runs/master-implementation-2026-10-10/openmp/install/lib/libomp.dylib`; retain that runtime with this binary. Its absolute path and hash are recorded in the baseline identity. Rebuilding is a new computational identity and requires fresh checks. The reproduction command on this Intel Mac is:

```sh
SEED_SEARCH_OPENMP_PREFIX="$PWD/runs/master-implementation-2026-10-10/openmp/install" ARCHFLAGS="-arch x86_64" .venv/bin/python native/build.py
```

The default build remains portable serial. A serial rebuild requires a compatible one-thread terrain setting; requesting unsupported native threading fails explicitly.

No supported implementation delivery checks remain pending. Optional scheduling/ISA/selection branches retain their measured defer decisions; game-evidence and intended mixed-workload gates remain open below.

Before a production sweep, acquire supported exact-build structure/recall evidence, complete natural V1/V2 controls with known relevant channels, and measured sustained resource/backlog headroom for the intended workload. Resolve these gates with current evidence and preserve pending work. No command in this delivery launches a production sweep.

For a supported actual positive import, use the separate executor:

```sh
.venv/bin/python -m seed_search.realm.recovery --run <run-directory> --index <completed-input-index> --evidence <positive-start-evidence.json> [--candidate <candidate-id>]
```

Omit `--candidate` only to recover in-discovery Stronghold centers. Supply trusted actual positive provenance, exact pinned world settings, the appropriate start convention, exact bounds, an artifact reference and SHA-256. This importer validates declared provenance and scope; it does not independently certify the provider. A successful import retains unresolved recall and actual Realm qualification. Refresh a frozen terrain pool through its explicit new-revision option when indicated. The executor resumes generation-free score recovery before ranked/export views become available.

Detailed implementation and measurements: [MASTER_IMPLEMENTATION_RESULTS.md](MASTER_IMPLEMENTATION_RESULTS.md). Reviewed tasks and acceptance gates: [MASTER_IMPLEMENTATION_PLAN.md](MASTER_IMPLEMENTATION_PLAN.md).
