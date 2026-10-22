# CPU and catalog readiness before GPU or storage-engine conversion

Status: PROPOSED, October22,2026. Requested planning/audit is complete; the implementation
below is not approved or executed by this document. Completed feature/organization
milestones remain complete. GPU conversion and a new database engine are separate
decisions, not a single required migration.

## 1. Decision and current baseline

First finish two measured bottlenecks—checkpoint serialization and guarded serving
read views—then prove CPU recovery/performance and define the GPU contract. Keep
SQLite control state. Benchmark a typed/columnar serving layout only where the new
read views remain limiting; choose an engine from target-scale evidence.

The [readiness audit](../reviews/pre-gpu-readiness-2026-10-22/AUDIT_MATRIX.md) checks
source,live state,test inventory,prior releases,old audit dispositions and hardware.
Current93snapshot feature options are available:56exact Overworld biomes,5Nether,
4groups and28structure choices including both validated variants. There are222saved
worlds/109918memberships;7543objectives allow115964primary/231928total membership
slots, not231928unique worlds. These capacities do not bound all historical storage.

Measured starting points (not future performance guarantees):

| Work | Current evidence |
|---|---|
|Personal34-thread scan |~75.7k/s paired alone;~69.1k/s withpublicworker+twoqueries |
|Current full public record |~32–35s per existing-world replay |
|Record breakdown |22.52s extraction/checkpoints,5.74s summaries,0.23s height,1.44s publication |
|Generic result-cache-miss query |2.25–4.59s on222worlds;warm0.07–0.10s |
|Precomputed board |~3.25s;~0.48ms narrowSQLitelookup prototype,notcompleteAPI |
|Current reachable/allautomation CAS |241MB/1036MB;older/shared objects are protected evidence |

See [benchmark](../reviews/current-framework-benchmark-2026-10-22/REPORT.md) and
[profile](../reviews/storage-query-profile-2026-10-22/REPORT.md). Short screening
cohorts produced one predicted survivor; full100-candidate natural scan cost is
unmeasured. Profiling perturbed one bounded8192search;onlyfixed-work comparisons
can require identical work/output. Frozen-observation derivation has exact snapshot
parity. Current-scale probes do not establish cold-disk or fleet capacity.

## 2. Work packages and order

### A. Freeze a reproducible CPU reference and resolve active-document drift

**Purpose:** avoid porting an old plan, a stale binary or an incomplete dirty checkout.
**Complexity:** small/medium; prerequisite for integration and GPU specification.

- Capture relevant tracked,untracked and required ignored source/config/tests,
  dependency locks,native inputs/build flags,binary/libomp digests and current
  snapshot/registry/profile/retention IDs in a restorable isolated source snapshot.
  Preserve previous evidence and failures. Verify restore in a fresh destination;
  do not reset,stash,clean,commit,push or move live roots automatically.
- Record current AMD Vega56/8GB iMac separately from proposed NVIDIA hardware.
  Confirm actual future GPU model/count/VRAM,host OS,driver/toolchain and access;
  historical fleet descriptions are not a verified deployment inventory.
- Freeze deterministic CPU/parity fixtures from the222saved worlds,existing
  generated-boundary fixtures and portable BDS controls. No newseed search required.
  Include public-useful/personal-failing worlds and nonempty personal positives.
- Separate fixed-work numerical oracles from wall-clock-limited operational tests.
  More work under the same time limit may alter search completeness; it must not
  silently change scoring or turn pending into complete.
- Refresh activeV3 status/navigation. Preserve frozen reports and conservative
  registry templates; current capability flags come from snapshot metadata.

**Done when:** restore/import/smoke checks pass in isolation, source/build IDs are
known,golden requests/results are saved,active docs agree with runtime,and hardware
requirements are explicit. No newGPU hardware purchase or production restart needed.

### B. Reduce extraction/checkpoint serialization and duplicate derivation

**Purpose:** improve useful-record throughput before feeding it faster candidates.
**Complexity:** medium; may run alongside C with separate ownership after A.

Primary code: `src/seed_search/catalog/harvest_native.py`,`extract.py`,
`refinement_queue.py`,`refinement_worker.py`,`summaries.py`; protocol/integrity changes
require coordinator review of `ingestion.py`,`models.py`,`artifacts.py`.

- Measure repeated full-observation hashing/JSON serialization,copying and validation
  at checkpoint/refinement boundaries. Distinguish bytes serialized,logical writes
  and actual disk I/O;the814MBprofile value is not physical write amplification.
- Reuse frozen data/derived calculations where identities match. Evaluate fewer
  whole-object rewrites or smaller versioned progress records under explicit bounded
  replay/lost-work rules. Preserve incremental durability,FULLsync,leases,heartbeats,
  partial states and source-bound checkpoints. Do not merely skip fsync or checks.
- Keep existing job/checkpoint readers or provide a versioned decoder/migration in
  a new private policy workspace. Never overwrite running/resumable jobs or reset
  their consumed budgets to obtain a faster benchmark.
- Compare fixed-work output and direct coordinate/coverage oracles;then compare
  unprofiled existing-world replays with the same work budgets and declared hardware.

**Done when:** exact facts/scores/coverage match for fixed work;crash/resume and
interrupted-write tests pass at each changed boundary;measured serialization and
record time improve beyond paired variability without worsening completeness or
resource bounds. Numeric speed targets are set from the reconciled design baseline,
not an invented promise of GPU-class throughput.

### C. Productionize snapshot-bound serving read views

**Purpose:** avoid decoding whole membership manifests and unrelated worlds per page.
**Complexity:** medium/high;read-model change,not a new database engine.

Primary code: `catalog/store.py`,`automation_query.py`,`service.py` and newread-view
module/tests. Keep exact `query.py` scorer initially;sharedartifact/schema ownership
belongs to Codex. Do not rewrite frozenV1/V2JSON contracts.

1. Start with precomputedboards:objective-local ordered memberships or indexed
   SQLite read projection,with primary/reserve/count/cursor behavior unchanged.
2. Add cheap typed feature/count/completeness candidate masks for personalized
   queries. Preserve same-anchor ALL andANYwithinrow;unknown candidates cannot be
   filtered out as negatives. Broad queries must have a nonregressing fallback.
3. Bind views/caches to snapshot,policy,registry,source,profile andvalidator revision.
   Preserve existing corruption detection beforewarmcache reuse,including checks
   of bound pages. Prototype timings omit someguards;no trust-boundary weakening is
   authorized to reproduce them. If a different integrity model is needed,review it
   explicitly before implementation.
4. Stage/fsync/checksum/index atomically before publication. Old snapshot/share/detail
   andcursor behavior remains usable;missing/corrupt/stale views failclosed or use an
   explicitly verified existing fallback. User queries never launch regeneration.

**Done when:** fullordered results—including unknowns,witnesses,exactties andviews—
match original scorable facts for all36products/72views and a frozen query matrix.
Corruption,stalebinding,expired/wrongviewcursor,concurrentpublication,workerfailure,
restart androllback checks pass. Rebenchmark completeAPI requests,notjustSQLlookup.
A proposed222-world goal isboard pages≤250ms andmeaningfully reduced cold generic
queries,whilekeeping10s allowance andboundedmemory;these are goals,notobservedSLAs.
No result may become faster by dropping validation or advertised requirements.

### D. Validate operations, retention and sustained CPU behavior

**Purpose:** establish a trustworthy baseline and ingestion capacity envelope.
**Complexity:** medium;depends on B/C integration. Reuse existing tests/oracles.

- Exercise100candidate capacity andcutoff propagation with oversubscribed synthetic/
  replay fixtures;compare pruned results against unpruned fullsort,including ties,
  deduplication,spill/restart,primary/reserve promotion and historical50capacity.
  Existing unit tests already cover mechanics;add only gaps exposed by changes.
- Exercise7543-objective2Kretention with nontrivial lower-cap/oversubscribed fixtures.
  Report actualdiscard fractions. All-worlds-retained results do not prove selection
  recall. Large real default-cap held-out recall remains a latercatalog-qualitygate;
  generating tens of thousands of CPUworlds is not prerequisite to aGPUprototype.
- Run bounded sustained current-code trials with/without actual public extraction
  and queries. Capture CPU/RSS/temperature diagnostics where available,actualoverlap,
  committedcoverage,queue growth,backpressure andusefulobservations/retainedworlds/hr.
  Separate rawseeds/s,selectedcandidates/s,completedrecords/s andAPI throughput.
- Test intentionallyslow/failingworkers,disk/output limits,corrupt artifacts,kills
  before/after SQLite commit andpointerpublication,budget exhaustion/resume,and
  restoration of a copiedcatalog/sourcecheckpoint. Protect pins,allreserves,
  historicalshares,verification-in-progress and old policyroots. No age-baseddeletion.
- Re-run affected Python/nativeparity tests duringdevelopment. Run thefull current
  catalog suite,appropriatepersonal/native suites,Nodecontracts andfrontend build
  once at finalintegration;repeat only fornewchanges/failures. BrowserQA remains
  waived under the existing instruction.

**Done when:** no introduced correctness failures;recovery/restore demonstrated;
fixed-work parity and bounded resource gates pass;sustainedrates and ingestion
backpressure are reported honestly. The personal backend remains preserved unless
an exact reviewed activation/restart is separately approved.

### E. Define the GPU contract and select the first one-device experiment

**Purpose:** accelerate eligible work without changing candidate populations.
**Complexity:** medium specification;actualport is a separate high-complexity project.
Can draft alongside B/C;final gate uses D's baseline.

- Define per-stageCPU/GPU ownership and independent personal/public admission.
  The supersededshared personalGPU rejection gate must not discard public-useful
  worlds. Public sampling/selection is independent of personal floors orcutoff.
  Any public earlyrejection needs a proof covering every remaining public objective.
- Freeze signed64seed identity/modulo arithmetic,PRNG behavior,placement/viability,
  negativecoordinates,floordiv8,half-openborders,circularnear-scopes,height/provider
  semantics andsameanchor scoring. Never clip factual counts to UIthreshold limits.
- Preserve 845/265/140 scoring,OW2048/4096/8192,Nether1024;2Kthroughscreening;
  unknown/partialstrongholds andsampledbiomecoverage;distinct dimensions/witnesses.
- Specify canonical batched input/output with versioned source/build IDs,coverage,
  completeness/errors,witness references,deterministic ordering/dedup andcheckpoint
  progress. Measure transfer/compaction/scheduling;don't assume bandwidth isfree.
- Choose a small isolatednativekernel after directunprofiledC/CFFI timing,not the
  wholeframework or aGPU-onlyrewrite. Retain CPUfallback/oracle. Oneactualdevice
  must pass declaredfixed-work parity andend-to-end useful-record gates before
  2/4/8GPU orfleet work. Nativeparity is not universalgameverification.

**Ready for GPUprototype when:** A/D pass,hardware isconfirmed,admission/parity/data
contract isreviewed,andtheone-deviceobjective/budgets/acceptance areapproved.
B/C shouldremove the demonstrated bottlenecks beforeclaiming ingestionbenefit or
scalingGPUoutput. A smallboundedkernelproof neednot waitfor all futurelaunchwork.

### F. Decide storage engine from the changed workload

**Purpose:** choose a read architecture after cheaper changes have been measured.
**Complexity:** medium comparative benchmark;not an automatic database migration.

- Keep SQLite forcontrol/queues/receipts unless measuredwriter/coordination limits
  establish a separate requirement. Precomputedboards use C's guardedreadmodel.
- If broadqueries remain dominated bydecode/scanning,benchmark typedimmutable
  ArrowIPC/mmap orsimilarstandardblocks;DuckDB/Parquet is an analyticalcandidate.
  Compare SAMEfacts/queries/scores/unknowns/cold&warmstates,includingbuild/update,
  sourceverification,recovery and storagecost. No engine has won that comparison.
- Declare intendedretainedworld count,membership/historygrowth,readers/writers,
  usefulingestionrate,latencytargets andavailablememory/storage. Test increasing
  labeledsyntheticreplicas andrealcohorts within approved budgets;distinguish both.
  Do not equate231928memberships with unique worlds or includeoldV2latency asV3proof.
- Reconsider ahand-written`.seedcat`engine orKVmigration only if measured standard
  readmodel/engine options fail a concrete target and the maintenance/recovery cost
  is justified. Distributedhosting needs its own workloadand deploymentdesign.

**Done when:** an architecturedecision records dataset/hardware/version/workload,
fullsemanticparity,completeAPIandwrite/recovery costs,alternativesandlimitations.
“No newengine needed” is a valid outcome. GPUprototype andenginebenchmarks can run
in parallel aftertheir own dependencies;neither presupposes the other'ssuccess.

## 3. Boundaries, resources, assignments and risk

This plan authorizes no newruntime work by itself. Before significantimplementation,
reconcile Gemini High objections and ask approval of the concrete phase/budgets.
No personalrestart,productionmigration,newBDS campaign,newlargeseedsearch,engine
installation,deletion,commit/merge/push or globalpermission loosening is included.

Suggested implementation decomposition (allworkers explicitHigh,isolatedsnapshots):

| Owner | Bounded work | Writable ownership |
|---|---|---|
|Codex |A,contracts,sourcepins,integration,finalreview,activationproposal |Sharedschema/artifactinterfaces,handoff/reports;review everypatch |
|Geminiworker1 |Bcheckpoint/derivation changes +focusedtests |Assignedharvest/refinement/summaries files only |
|Geminiworker2 |Cserving readviews +focusedtests |Assignedstore/service/query-adapter files only |
|IndependentHighreview |One source/acceptance review at integration |Read-only,nooverlappingimplementation |

Do not dispatchallworkers merelyforconcurrency. B/Cmustagreeonartifactinterface
beforeparallelcoding;sharedfilesneedoneowner. Codexindependentlyruns meaningfulchecks.

Proposed CPUacceptance-measurement envelope to review before execution:reuse≤5existing
worlds percomparison,≤120s/world and≤600s cumulative extraction percomparison;
4GiBaggregateownedRSS/2GiBnewoutput excluding an explicitlybudgeted read-onlyinputcopy;
fixed10squerydeadline/cache/IPC caps;bounded5–10minute screening/loadtrials inprivate
roots. These are proposed new allocations,not permission toreset previousspentbudgets.
BDS remains0newruns unless separatelyreviewed. Finaltest budget isestimatedfrom
existingcatalog~5min plusaffectedtests/build;workers getexplicit≤15min tasks/retries.
Do notexpand limits ontimeout;savepartialresults andreturn to thereviewedplan.

Main risks:formatmigration/resumecompatibility;cacheguardweakening;Decimal/rank
precision;budget-dependentcompleteness;sharedfileconflicts;syntheticbenchmarks
misread aspopulationproof;GPUadmissionfalse negatives;unboundedhistory;unconfirmed
GPUhardware. Mitigations andacceptance above are required,not optionaloptimizations.

## 4. Work that is separate from this transition

No additional genericfeatures,fullstrongholdpredictor rewrite,terrain/safety guarantees,
largeBDSfinalist campaign,paidaccounts/payments,publichosting,customengine ormassive
cataloggrowth isrequired before the firstGPUparityexperiment. Their existinglimitations
remain visible. Actualadvertisedverifiedfinalists require scopedgameverification;
publiclaunch additionallyneeds deploymentsecurity,backup/restore,ownership/limits,
realisticload andproduct QA. Interactivebrowser waiver doesnotauthorize apublicSLA.

Safe repoorganization is complete. Keepcanonicalsource/test/evidencepaths;more
physicaldecluttering isnot aGPUprerequisite. A restorable dirty-sourcebaseline matters
more than manufacturing acleanGitstatus.

## 5. Transition gate checklist

- [ ]A:restorable currentCPU/reference+dependency/build/data manifest.
- [ ]B:measured serialization/derivation improvement withcheckpoint crash/resume parity.
- [ ]C:guarded productionreadviews withcompleteAPI/result/cursor/integrity/recovery parity.
- [ ]D:capacity,retentionmechanics,sustainedload/backpressure andcopiedrestore checks pass.
- [ ]E:confirmedGPUhost/device plus independentadmission andfixed-workparity contract.
- [ ]One-deviceGPUproposal approved;no fleetconversion until measuredacceptance passes.
- [ ]F:target-scale storagebenchmark/decision before anyengine replacement.

Approval ofplanning doesnotcheck off implementation boxes. Fullproductioncatalog
recall,publiclaunch andphysicalgamecertification have separate evidence gates.
