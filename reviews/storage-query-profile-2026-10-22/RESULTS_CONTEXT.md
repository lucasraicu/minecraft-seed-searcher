# Measured results for neutral interpretation review

User asks profiling current costs and storage/query bottlenecks to guide GPU and
whether/which custom DB. No production code/schema/native changes authorized.
Current source/native pins unchanged, live222world snapshot copied and verified.

Existing world current unprofiled pipeline32.427s: extraction22.515s (includes
checkpointing,spawn,Realm/refinement),extra height0.227s,summaries5.742s,publish1.445s,
other2.498s. cProfile+counter run52.481s;child JSON output814176679bytes/4105dumps,
finalcheckpoint8.63MB, fsync624calls0.241s. General visible native calls2.92profiled
seconds. No sum of nested counters; opaque CFFI/executable and profiler distortion
prevent GPU speedup prediction. Profiled8192 bounded search362vs552centers, budget
flag changed;selected result same but full semantic equality failed. Preserve this
as instrumentation perturbation. Fixed frozen-observation derivation replay added
within900s to get exact snapshot equality without extra base extraction.

Current reachable compressedCAS241264651bytes:222world bundles167807583,
666query projections51738239,membership pages21618766 raw79425305JSON bytes.
All automation objects1036457363bytes;difference includes historical/shared/orphans,
NOT disposable proof. Entirecatalog~1.27GB. SQLiteharvest111800320bytes,109918members,
222receipts,no free pages,noqueuejobs;controlwritecontention not measured.

Fiveactualquerytypes,3unprofiled trials each at10s:Origin~2.25s,broadRecommended~4.59s,
mixedvariants~3.34s,biomeOR~4.23s,selective~3.46s. Warm0.07–0.10s. CPU~=wall.
Counter-only broad4.270s:JSON2.258,read+hash0.205,inflation0.131;42MBverifiedwire,
82MBparsedJSON perbroadrequest. Mixed3.032s:JSON2.166. Countersnested notadditive.
Raw read/inflate/parse micro retained wholemanifest and had higher GC cost than
production-shaped counter-only call;do not addmicrostages tolatency orclaimdiskcold.

Existing precomputedboard5rows:3.15–3.43s,profile mostlyfullmanifestrehydration/
validation. DisposableSQLiteWITHOUTROWID membershipindex109918rows builds1.65s;
lookup+payloadJSON+role+metadata check~0.5ms,7repeats/primary+reserve,exactfirstpage
payload parity. This is not completeHTTP/cursors/crypto-validation/recovery/engine
comparison. Cached in-memoryBLOBlookup also measured. No drop-in speed guarantee.

OneborderRecommended17983anchors. ConservativeSQLcounts/complete prefilter + ORIGINAL
scorer yields same fullorderedresults+pending. Mixedtwo-requiredvariants:270anchors,
17worlds;selectedblobload+scoring0.254s vsbaselinecurrentAPI3.34s, excludesstartup/
crypto-bindingguard/indexbuild. Broadallworlds blobloading8s inside RAM-heavy
ablation vsAPI4.59s: do NOT claimgeneral speedup or comparable cache/allocation.
0matchselective retained0rows (trivialspeedup);biomeORdoesnotprefilter missingness.
ActualSQLplanSCANfilters at18krows;indexesnotusedforORknown predicates; don't say
Btree acceleration for thisfilter. Numericarraymask~0.3–0.7ms but narrow3features,
notcompletecustomengine. Four syntheticcontrols passsameanchorALL,unknownpending,
knownnegative,positive. Actualfinitefullresulttie/precision equality usesPython
Decimal unchanged, originalJSONoracleexport initiallyfailedDecimalserialization;
recoveredexacttaggedDecimalexportwithoutrepeatingtimingtrials,logs preserved.

Tentative recommendation to critique: keepSQLitecontrolstate;indexedprecomputed
readviews now;typedimmutablecolumnarservingblocks/vectorizedranking candidate next;
Arrow IPC/mmap + optionalDuckDB/Parquet scale benchmark, no measuredenginewinner.
No need demonstrated for newhandwritten.seedcat orRocksDB migration. Firstreduce
CPUcheckpoint/JSON/summary duplication;thenone-deviceGPU parity+usefulrecords/s
benchmark, not solelyrawscreening. Current222worlds RAM-resident cannotchoose
fleetengine or inferdiskcoldproductionSLA. No newDB installed or runtime integrated.
