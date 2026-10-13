# Complete native baseline prototype: parity and measured throughput

Measured 2026-10-12 on the local Intel Xeon W-2191B: 18 physical cores, 36 logical CPUs, 64 GiB RAM. This implements the proposed **complete native baseline evaluator behind a Python interface**, as an isolated experiment. The experiment and conversion are the same work; parity and performance checks precede production adoption.

**Decision: retain the existing production path.** The private C evaluator reached **19,835.874 input seeds/second** with 36 OpenMP threads, but its first complete persisted adapter reached **948.426/sec**, versus **1,174.968/sec** for a fresh run of the existing 30-process path. That is **19.28% less persisted throughput**, despite much lower observed memory use. Moving generation/filtering into C succeeded; this adapter does not yet deliver a faster complete search. No production dispatch, source bridge or production extension was replaced in this task.

## Implementation and scope

`native/blueprint_batch.inc` includes the existing pinned C bridge in a separate private extension. A single call accepts a bounded full64 seed array and runs the complete blueprint baseline:

1. Stronghold discovery, sorting/deduplication and evaluation of every discovered anchor.
2. Exact Stronghold-centered 1536×1536 Overworld and fractional Stronghold/8-centered 896×896 Nether bounds.
3. Ordered viable count floors, full Mansion inventory plus exact Dark Forest filtering, and early exits for missing model evidence.
4. Joint final Nether Fortress/Bastion observations.
5. The exact world-aligned four-Y lattice, role-specific biome families, dispersed sample order, batch stopping and first witnesses.
6. Complete required inventories, optional Outpost and capped count bonuses for full baseline survivors.

Each OpenMP thread owns one `SeedContext`, its Overworld/Nether generators and reusable scratch storage. It reapplies the full64 seed before each input. The existing MT state is thread-local; no viability results or low-bit biome evidence cross seeds. An atomic counter assigns chunks of 16 inputs, and results stay in original input order. Each returned batch owns its result buffers until `nb_free`. Allocation/query errors fail the batch before any range can be committed; capacity overflow is an error rather than truncated evidence. The normal entry point never calls the explicit synthetic fixture provider.

The first attempt using `schedule(dynamic,16)` exposed an ABI mismatch: this compiler emitted `__kmpc_dispatch_deinit`, which the pinned local OpenMP runtime does not export. Explicit atomic chunk claiming preserves dynamic work distribution using the runtime's supported parallel region. The builder now verifies actual extension loading, not just compile/link success. The pinned production runtime was not changed.

Python reconstruction deliberately reuses the existing evaluator's record-building logic with a read-only provider containing C results. **It makes no generation calls.** C has already calculated count failures, biome masks, first witnesses and scores; the adapter verifies reconstructed decisions against those native outputs. This preserves the current detailed evidence schema while testing the computational rewrite, but costs Python time. The native biome loop currently does not cache overlapping anchors' sample points; the adapter's logical cache preserves existing record/cache-hit semantics. This is a performance limitation, not alternate biome evidence.

The persisted adapter uses the existing `RealmStore` tables, FULL-synchronous SQLite transactions, range leases, signed seed strings, pending discovery tasks, pending candidate records, V1 tasks and resume identities. It stores every processed input and every discovered anchor, not only winners. Compiled-extension, policy, adapter and production-record computation identities protect new experimental checkpoints. Timing records created before the final identity metadata addition are retained as their original evidence; the addition changes checkpoint identity metadata, not generation/filtering or reconstruction decisions.

The private extension is loaded explicitly from its build identity and checked by hash. It lives under `runs/native-blueprint-prototype-2026-10-12/native/`; production does not import it. Portable serial builds remain supported and reject parallel requests. Terrain and actual Bedrock verification are outside this prototype.

## Correctness verification

The complete integrated regression suite passed: **781 tests in 125.29 seconds**. Eight new prototype tests cover:

* Real extreme signed-64 seeds, high-bit siblings, optimized and complete/reference modes, detailed coordinate inventories and bonus caps above their caps.
* Independent Python/C synthetic passing fixtures, all twelve non-anchor required count failures, all thirteen missing biome predicates, wrong-Y witnesses and Pale Garden-only Mansion failures.
* A Pale Garden Mansion decoy preceding qualifying Dark Forest starts; a later valid start must not be hidden by an early count cap.
* Negative discovery-edge and upper-edge centers, world-lattice boundaries and exact fractional negative Nether bounds.
* Repeated UINT64_MAX inputs mixed with different seeds across multiple thread counts, input-order preservation and context isolation.
* Invalid inputs/policies, closed batch ownership, complete checkpoint evidence, no-work resume and incompatible resume rejection.
* A fresh portable serial build in a separate interpreter and production-extension hash preservation.

**AddressSanitizer: 576 inputs, zero buffer/use-after-free errors**, in an isolated serial executable. It exercises real inputs and synthetic positive/negative paths repeatedly in both optimized and complete modes. Leak detection is disabled because that feature is unsupported by this macOS ASan runtime; this does not constitute a leak or race certification.

The benchmark's three cohorts contain **30,000 distinct full64 inputs / 55,853 discovered anchors**. No full baseline survivor was found. Native decisions matched across all thread settings and repetitions. Full persisted semantic record fingerprints matched across both implementations and all repetitions: **90,000 native records compared against 90,000 Python records**, reusing the same 30,000 distinct inputs. Comparisons include complete evidence fields and counters; implementation-specific timing/resource/prototype annotation fields are excluded. They do not establish actual Bedrock precision/recall or a full-blueprint passing world.

Synthetic passing fixtures test the complete controller and ranking path without pretending to be actual Minecraft worlds. Real complete-mode tests additionally exercise native downstream generation on inputs which would ordinarily exit early. No natural complete survivor was available for a conditioned downstream benchmark.

## Native-call throughput

Three disjoint 10,000-input permutation cohorts use run keys 120260001000, 120261001000 and 120262001000. Each profile has three sequential repetitions per cohort. Aggregates divide 30,000 by the sum of the three median cohort times. Batch size is 4,096; warmups reuse a 64-input subset. Repetitions and warmups add no distinct search volume. Actual team sizes are recorded and asserted to equal the requested sizes.

| Native threads | Aggregate input seeds/sec | Scope |
|---:|---:|---|
| 1 | **1,205.745** | Private C batch calls |
| 18 | **16,486.887** | Private C batch calls |
| 36 | **19,835.874** | Private C batch calls |

Timed native calls include OpenMP/context setup, complete applicable baseline computation, all discovered anchors and output-buffer allocation. Seed array/policy preparation and diagnostic result extraction occur outside those timers. They exclude Python evidence reconstruction, IPC, SQLite, terrain and BDS. Native output arrays and filtering order use exactly the required blueprint contract; this is not a raw-placement-only speed figure. Nevertheless, the rare downstream gates were unentered on this cohort. These are bounded short-run measurements, not guaranteed sustained production rates or useful world yield.

## Complete persisted comparison

Fresh runs use the same three cohorts and three repetitions. Arm order alternates by repetition. Builds/tests ran separately from timing trials. Both arms write the existing complete `RealmStore` evidence schema. The existing implementation uses 30 processes, one native thread per process and batch size 32. The native prototype uses one Python parent, 36 OpenMP threads and batch size 256. This compares actual candidate workflows, including their different scheduling and batch choices; it does not isolate every individual optimization.

| Complete persisted path | Input seeds/sec | Peak observed process-tree RSS | One million input projection |
|---|---:|---:|---:|
| Existing Python/process path | **1,174.968** | 1,473,859,584 bytes | **14.18 min** |
| Private C batch + Python reconstruction | **948.426** | 279,826,432 bytes | **17.57 min** |

The prototype's observed peak RSS was approximately **81% lower**. Process-tree RSS sums can count shared pages twice; short-run peaks are not memory ceilings. Monitoring uses the same existing process-tree resource reader. No long-run memory stability or portable-host rate is inferred.

The prior 1,238.23/sec pilot is a different timing session; this fresh repeated comparison measured 1,174.97/sec. The performance decision uses the concurrent-task-free fresh comparison, not the earlier number. Full evidence matched despite implementation-specific metrics and prototype annotations. Average SQLite bytes per 30,000-input repetition were about 430.52 MB for Python and 449.88 MB for the prototype; prototype annotations and timing/resource representations differ. Full unresolved evidence is retained in both.

For the native persisted adapter, summing median service times across the three cohorts gives:

| Service, per 30,000 inputs | Time | Execution behavior |
|---|---:|---|
| Native batch calls | **3.494 s** | Includes smaller-batch context/team overhead |
| Python evidence reconstruction | **9.850 s** | Runs in the parent |
| Range commit/serialization/persistence | **17.517 s** | Runs in the parent |

These service medians need not sum exactly to the median total: sample medians are calculated separately, and configuration/range/seed/checkpoint work also costs time. The first adapter runs these services sequentially. The existing process pool overlaps worker computation and record construction with parent persistence. Its useful comparison is the measured full wall time, not a sum of independent native kernel rates.

The **19,836/sec C rate is therefore not a 19,836/sec persisted rate**. Eliminating Python generation calls is insufficient while detailed record reconstruction and persistence dominate the parent. Discarding unresolved inputs, dropping anchors, weakening required predicates or calling a raw placement gate the full baseline would make an invalid speed comparison.

## Adoption and the next justified optimization

Production remains on the existing evaluator. The isolated native evaluator is available for further development; its result currently justifies **profiling and redesigning evidence construction/persistence**, rather than integrating terrain or replacing a faster production path. A future experiment could generate reusable serialized evidence in C and accept it through a carefully validated bulk checkpoint adapter, or pipeline native work and record construction while preserving full coverage, uncertainty, scoring and resume guarantees. Those alternatives need their own full-record parity and complete persisted benchmarks; no speedup is claimed for them here.

Neither million-input projection predicts time to a fully qualifying playable world. The full success probability remains unknown, and terrain/BDS service costs are excluded. See [BLUEPRINT_FEASIBILITY_ANALYSIS.md](BLUEPRINT_FEASIBILITY_ANALYSIS.md) for that distinction. The full fixture/real-record parity suite is valuable evidence of compatibility, not certification of a discovered world.

## Reproduction and evidence

Private artifacts: [runs/native-blueprint-prototype-2026-10-12](runs/native-blueprint-prototype-2026-10-12/). The receipt records exact source/runtime hashes and measured scopes. Large generated databases and binaries remain local benchmark evidence.

```sh
.venv/bin/python scripts/build_blueprint_batch.py --output runs/new-native-blueprint/native --openmp-prefix runs/master-implementation-2026-10-10/openmp/install
.venv/bin/python scripts/benchmark_native_blueprint.py native --native runs/new-native-blueprint/native --output runs/new-native-blueprint/benchmarks --count 10000 --trials 3 --threads 1 18 36
.venv/bin/python scripts/benchmark_native_blueprint.py persisted --native runs/new-native-blueprint/native --output runs/new-native-blueprint/benchmarks --count 10000 --trials 3 --persist-threads 36 --persist-batch-size 256
.venv/bin/python scripts/sanitize_blueprint_batch.py --native runs/new-native-blueprint/native --output runs/new-native-blueprint/asan
.venv/bin/python -m pytest -q
```

Omit `--openmp-prefix` for an isolated serial build; parallel requests then fail explicitly. Use fresh benchmark directories and run timings without competing builds/tests. The runtime-prefix argument is an explicit local dependency, not a generic installation path for other hosts.

* [Native timing records](runs/native-blueprint-prototype-2026-10-12/benchmarks/native-throughput.json)
* [Persisted timing and semantic fingerprints](runs/native-blueprint-prototype-2026-10-12/benchmarks/persisted-throughput.json)
* [ASan receipt](runs/native-blueprint-prototype-2026-10-12/asan/result.json)
* [Final test log](runs/native-blueprint-prototype-2026-10-12/final-pytest.log)
* [Consolidated verification receipt](runs/native-blueprint-prototype-2026-10-12/summary.json)
