# Production dynamic-envelope-1664-v1 audit

Audited checkout: `54b7d63`, 2026-10-15. Production source and configuration were not edited. The default web engine is `runs/dynamic-baseline-1664/native`; every available input hash in its build identity matched the checkout. Its binary and OpenMP runtime passed the adapter's identity validation. This is a source-matched Clang 17, native-CPU, PGO+LTO, x86-64 build. All proposed changes below remain unapplied.

## Verified Critical Discrepancies (P0/P1)

No P0 verified. Three P1 findings are reproduced.

### P1-1 — Python ranks optional structures at the wrong center

File: `src/seed_search/realm/dynamic.py:82`:

```python
        if name in OPTIONAL_NAMES:continue
```

File: `src/seed_search/realm/dynamic.py:115`:

```python
            rows.append(Candidate(snapped,density,counts,deficits,radial))
```

`counts` is calculated at the nearest-origin representative on lines 92–94, before centroid snapping. Optional structures do not contribute event boundaries, so their counts need not remain constant during snapping. The final Python ranking uses these stale counts at `blueprint.py:526`:

```python
                score=dynamic_score(item.counts,palette_index.luxuries(center),hub_bonus(structures,center))
```

C instead counts optional structures at the snapped center (`native/blueprint_dynamic.inc:454`):

```c
        for(int k=0;k<5;k++)score+=optional_points[k]*nb_dynamic_count(&optional[k].viable,x,z,832,0,NULL,0);
```

**Reproduced numerical trigger:** extend the existing `DynamicFixtureBackend` and corresponding native fixture with one viable swamp hut at `(56,-800)`; seed label 123, fixture `(0,0,-1)`, missing mask 0, deficit depth 1, default policy. The only native fixture modification supplies that optional point; production selection code is unchanged. C selects `(-752,-816)` with score **434**, while the independent Python evaluator selects `(-784,-816)` with final score **422**. The latter's eastern boundary is 48, excluding the hut; the former's is 80, including it. This is a synthetic coordinate regression, not a claim that natural seed 123 has those structures.

An additional distinct-coordinate example puts each required category's default number of starts at `(0,16*i)` and a hut at `(840,0)`. Python ranks `(80,48)` first; evaluating optional counts at the actual candidate centers ranks `(16,48)` first. Within lattice cell `[1,65)`, center 8 excludes x=840 and center 16 includes it.

**Minimal parity fix**, immediately after `snapped=tuple(axes)`:

```python
            snapped_bounds = overworld_bounds(snapped)
            for name in OPTIONAL_NAMES:
                counts[name] = sum(contains(point, snapped_bounds)
                                   for point in inventories.get(name, ()))
```

Applying this change only in the diagnostic Python wrapper restored the native result `(-752,-816), 434`. Mandatory counts, centroid membership, lattice events, and half-open bounds remain intact.

**Scope of the geometry claim:** current equivalence cells preserve mandatory structure counts and biome witnesses, not optional counts or the circular hub score. If the blueprint's “every discovered structure” language requires optional-count invariance too, optional inventories must be available before constructing events, their entry/exit events must be included in both implementations, and C event-buffer sizing must include them. Merely recounting fixes current native/oracle parity but does not implement that broader partition. The centroid representative is the specified policy; it is not a proof of global score optimality over every snapped point.

**Why existing replay checks miss this:** `native_batch.py:326` assigns the C-selected `dynamic_center` to ReplayProvider, and `blueprint.py:520` runs the independent candidate search only when `replay_center is None`. Replay verifies evidence/score reconstruction at an already chosen center, not independent selection.

### P1-2 — Dynamic worker allocations bypass max_buffer_bytes

File: `native/blueprint_dynamic.inc:78`:

```c
        w->dyn_prefix=malloc(23*side*side*sizeof(int));
```

The same bypass occurs for biome grids, Nether prefix/grid, event arrays (line 380), and cells (line 412):

```c
        w->dyn_cells=malloc(w->dyn_cells_cap*sizeof(NBDynamicCell));
```

These allocations bypass the atomic reservation in `native/blueprint_batch.inc:72`:

```c
    if(previous>w->p->max_buffer_bytes || bytes>w->p->max_buffer_bytes-previous)return NULL;
```

**Reproduced numerical trigger:** one default survivor fixture, seed label 123, `(0,0,-1)`, mask 0, one thread, `max_buffer_bytes=1,400,000`. The batch succeeds and retains one anchor while requested live native allocations peak at **1,872,336 bytes**. The instrumentation excludes allocator metadata and the separately allocated SeedContext, so this is a conservative lower bound. It counts simultaneous live allocations, not cumulative allocation traffic. After `nb_free`, tracked live bytes return to zero; this is a reservation-contract violation, not a demonstrated leak.

**Minimal fix:** allocate all dynamic buffers through `nb_alloc(w, bytes, 0)` and retain per-worker reuse. Keep the deliberate monotonic reservation semantics. If the cap is intended to cover every owned native allocation, reserve the fixed per-thread SeedContext cost as well; otherwise explicitly document its exclusion. Do not increase the cap as a substitute for enforcement. Combine this with failure-safe capacity publication below.

### P1-3 — Allocation failure poisons reusable capacity and crashes the next seed

File: `native/blueprint_dynamic.inc:381`:

```c
        w->dyn_ex_cap=ex_need;
```

File: `native/blueprint_dynamic.inc:411`:

```c
        w->dyn_cells_cap=maxcells+1024;
```

Both publish a successful capacity before confirming allocation. `nb_run` continues evaluating later seeds with the same worker after an input error. On the next equal-or-smaller request, the capacity guard passes and a null pointer is used.

**Reproduced numerical trigger:** two survivor fixtures `[123,123]`, both `(0,0,-1)`, mask 0, one thread, 256 MiB cap. One-shot failures at allocation 34 or 35 (each **11,696 bytes**, event buffers), or allocation 36 (**77,928 bytes**, cells), each produced subprocess return code **-11 / SIGSEGV**. Prefix/grid allocation failures at calls 37–40 instead returned error `-3` and cleaned up successfully. Fault injection changes allocation success only, not solver decisions.

**Minimal fix:** allocate replacements into temporary pointers; on failure free only those temporaries and return `-3`; on success free old buffers and publish both pointer and capacity together. Apply to event-pair and cell-buffer growth. Alternatively reset pointer and capacity to zero before growth, but do not leave stale nonzero capacities. Returning the batch error must remain mandatory; no partial batch may be committed. Existing SQLite transactions keep previously committed ranges intact, but the crash violates graceful failure/recovery expectations.

## Pragmatic Architecture Verdict

**Keep C11/OpenMP and contiguous arrays.** A SeedContext, mansion cache, stack-local NBWorker, and reusable dynamic buffers belong to one OpenMP worker. Python creates a call-local NBPolicy copy. Atomic chunk claiming gives workers disjoint output indices; the two shared atomic counters are intentional shared state. No ordinary-path shared-generator race or persistent native leak was reproduced. Arrays need no tree or spatial hash. There are no hardware-counter measurements in this audit establishing cache/memory-bandwidth saturation or a false-sharing bottleneck, so neither padding nor a new data structure is justified.

The fixed raw-preflight scratch arrays are about 7 KiB on the stack; large prefix/event/cell buffers are on the heap. Correcting heap reservation and allocation failure is more important than moving these arrays between stack and heap. Dynamic worker buffers live for one native batch, not across all batches.

**Verified mathematics:** Overworld membership gives center interval `[X-831, X+832]`; Nether membership gives `[8*N-3327, 8*N+3328]`, inclusive integer-center intervals with exit events one later. Negative coordinates use floor/ceiling arithmetic. Every emitted center is a multiple of eight, so rational center/8 and center//8 agree for production outputs. The Python helper intentionally preserves rational geometry for unsnapped diagnostic inputs. Both axes' lattice memberships were checked at every integer center in `[-1168,1168]`. All **160 raw lattice entry/exit contributions per axis** are generated: `2*63+2*17`. They clip and deduplicate to **37 distinct interior boundaries**, which is correct and does not remove a membership transition. The +30 second-monument expression matches in both implementations. Forty-four bonus masks and six strict monument rejection cases passed direct native checks. Raw-Nether union bounds also passed the existing 24-case exhaustive aligned-center test and 256 shared-placement comparison cases.

**Measured hot path:** three disjoint 100k-input current-binary trials ran at **46,943 / 50,439 / 49,749 seeds/sec**, 34 threads and 16,384-input batches. About **80.6–81.0%** of summed per-seed elapsed time was Mansion evaluation, about **4.6%** raw-preflight/final-Nether stage time, and **0.013–0.052%** dynamic center search. These are inclusive timing observations, not hardware cycle or cache-miss attribution. All natural performance cohorts rejected; they do not establish survivor frequency or rare-survivor cost.

Rust wrapping the same C kernel offers no intrinsic kernel acceleration. A rewrite must justify itself through measured algorithm/code-generation changes or ownership benefits, not language choice. GPU execution is not demonstrated to be slower or faster here: noise/viability divergence and host transfer costs are risks, not a speed theorem. CUDA documents divergence costs, but only an implementation benchmark can establish the crossover. A raw-placement-only GPU stage addresses a small measured fraction of this workload. AVX2 for rare cell membership scans cannot materially move aggregate throughput here; even eliminating the measured cell stage gives less than roughly **0.06%** on these cohorts. Do not change noise floating-point expressions or integer random arithmetic without parity evidence. [CUDA primary documentation](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/index.html#branching-and-divergence).

**CFFI:** the generated wrapper has `Py_BEGIN_ALLOW_THREADS` / `Py_END_ALLOW_THREADS`; native generation releases the GIL. `ffi.buffer` hashes verdict storage without an extra data copy. The pipeline is not entirely zero-copy: Python constructs seed lists and `ffi.new('uint64_t[]', ...)`, and retained evidence becomes Python records/JSON. The batch boundary itself is amortized over 16,384 inputs. Across the durable trials, seed preparation consumed 0.136–0.154 seconds per 100k, while generation consumed 2.02–2.07 seconds. This does not justify replacing CFFI. [CFFI buffer ownership/reference](https://cffi.readthedocs.io/en/latest/ref.html#ffi-buffer-ffi-from-buffer).

**SQLite and orchestration:** the native executor has one producer thread and one preparation thread; the calling writer thread owns SQLite. Preparation uses cached policy and makes no database calls. WAL/FULL, atomic records+receipt+coverage commits, the OS scan lock, and retryable leases are suitable here. Three fresh durable 100k-input runs committed all inputs, passed `PRAGMA integrity_check`, and had no unfinished ranges. Throughput was **43,949 / 42,380 / 42,991 inputs/sec**; writer service took **45–52 ms**, including only **3.5–3.7 ms** of measured range commits. These sparse all-reject runs are not evidence of a saturated SQLite writer, nor a long-duration soak. Do not weaken FULL durability. WAL permits readers alongside a writer, still has one writer, and checkpoint progress can be delayed by long readers; journal size limits are not an unconditional live-WAL cap. The web reader connections are short-lived. [SQLite WAL documentation](https://www.sqlite.org/wal.html).

**Verified lower-priority issues:**

- **P2, actual in-flight bound is one higher than reported.** `native_batch.py:504`, verbatim `while len(pending)<inflight and submit(store):pass`, executes after popping the current item. With count=4, batch_size=1, inflight=3, observed outstanding ranges at commits are `[4,3,2,1]`, while the reported maximum is 3. This remains bounded, but invalidates three-batch memory accounting. Minimal fix: remove that early refill (the post-commit refill already exists), or count the current item against the limit.
- **P2, web cache ignores updates.** `web/server.py:532`, verbatim `if getattr(self, '_last_candidates_sig', None) == sig and self.candidates:`, uses row counts/max(rowid). Candidate `123:0:0`, seed 123, score UPDATE 100→130 leaves those signatures unchanged: DB leaderboard score becomes 130 while the next candidate query still returns 100. Minimal fix: refresh the bounded top-250 query on polling, or use a durable revision incremented with updates. `PRAGMA data_version` on a newly opened connection is not a sufficient replacement.
- **P2, active README scoring description is stale.** `README.md:16` contains verbatim `**20 per Bastion above three**, and **5 per qualifying Shipwreck above five**`. At bastion count 3, implementation/spec award 20 while that text implies 0; at shipwreck count 6, implementation/spec award 0 while text implies 5. Minimal fix: describe a one-time +20 third-Bastion milestone and +5 for each Shipwreck above six. The code should retain the correct current formulas.

## Top High-Impact, Low-Bloat Micro-Optimization

**Delay generator seeding until the corresponding viable scan needs it.** The raw Nether and raw Overworld preflights use `w->ctx->seed` and `getStructurePos`, not the noise generators. Currently both generators are seeded before raw rejection. The supplied [lazy-generator.patch](lazy-generator.patch) moves Overworld initialization after compact raw preflight, preserves early initialization for full-evidence Stronghold discovery, and initializes Nether immediately before `nb_nether`. No events, tolerance, coordinates, random algorithms, or inventories change.

Both comparison arms used 34 threads, 16,384-input batches and source-matched native-CPU PGO+LTO. The experimental arm was trained with the same 10k-input cohort and positive fixture used by `rebuild_pgo.py`. Five alternating paired trials used disjoint 100k cohorts at permutation indices 20,000,000–20,499,999 with run key 2026101401, disjoint from training. Current median: **51,191 seeds/sec**. Experimental median: **56,326 seeds/sec**, a **10.0% ratio-of-medians gain**. Individual paired gains were **7.2–12.0%**. Every decision-receipt fingerprint matched. Forty synthetic cases in each of full and compact retention matched, as did 256 independent natural full-evidence records.

Projection from the user's 47.8k baseline: approximately **51.1k–53.5k seeds/sec**, with **52.6k** at the measured median ratio. This is a kernel projection, not a durable throughput guarantee. Fix the P1 findings before adopting/retraining this change. No second aggregate-throughput optimization meets the evidence bar in this audit. Maintaining the best cell directly could remove the cell array and simplify its allocation risk, but the measured event-cell fraction does not justify calling it a high-impact speed improvement.

## Production Readiness Sign-Off

**FAIL for an unconditional production sign-off.** Three reproduced P1 findings break independent oracle selection, the explicit buffer reservation contract, and recoverable native allocation failure. No P0, committed-range corruption, or ordinary-path shared-generator race was verified. The underlying half-open mandatory geometry, complete biome lattice transitions, +30 monument score, CPU architecture, and transaction model are sound within the checks performed.

**Verification completed:** 225 existing targeted tests passed, covering dynamic geometry/oracle fixtures, raw-placement parity, native batches/retention/build hardening, SQLite storage and recovery, worker/memory policies, and web controls/evidence. Additional probes reproduced all three P1s, checked lattice intervals exhaustively in one dimension, exercised score masks, verified lazy-initialization parity, and completed three durable scans with integrity checks. No multi-hour soak, ThreadSanitizer run, exhaustive full64 seed enumeration, or live BDS generation verification was performed. Prediction remains distinct from actual Bedrock certification.

Evidence is in [evidence.json](evidence.json); diagnostic scripts are in [probes](probes). Run them from the repository root with `.venv/bin/python`. `build_probe.py` builds the isolated allocator-instrumented extension in `/tmp/minecraft-audit-20261015`; `probe.py 1400000` reproduces cap bypass. Run `probe.py 268435456 34 2` in a subprocess with core dumps disabled to reproduce the allocation-failure crash (35 and 36 also reproduce). `build_optional_probe.py` adds the single optional fixture point to an isolated native copy, then `PYTHONPATH=.:src .venv/bin/python reviews/codex-audit-2026-10-15/probes/optional_probe.py` reproduces the center mismatch and the minimal recount correction. These are diagnostic fixture changes, not production source edits.
