# Measured larger-load resource addendum
User approved larger ingestion/retention/restart/query validation. First50full243
worlds completed123.72s,174MB;200completed500.31s,252MB,31.8MBoutput. All18 indexed
cold/warm query results match exhaustive oracle. One full1000-world corpus should
take roughly2500s by linear projection, subject to immutable publication overhead.
Original900s pilot cap cannot honestly complete it. Increase ONLY disposable
operational harness configurable maximum to3600s; per-call positive validation,
4GiB RSS/4GiB output,worldcap2000,batchcap10 retained. Execute1000worlds once,
not2000, no natural seeds/BDS/GPU. Context: diverse templates fromall200retained
worlds,syntheticidentity,243layouts each. No fabricateddata inlivecatalog.

Wall checks beforeeachbatch/query, outer process watchdog at3660s to include
cleanup; preserveprogressonfailure, noautomaticrerun orclaimpartialsuccess.
Known limitation: internal beforeoperation checks aren't hard deadlines inside
one operation, hence outer watchdog. Do not compare harness query_seconds=3600
withdefault10s serving SLA; measuredefaultHTTP separately andreporttimeouts.
Reportactualp50/p95 from18queries andRSS/disk,notproductionlatencyguarantees.
Existing200-world defaultHTTP8simultaneousrequests:2success,6explicit429;
4×50paginationexactordered200worlds. Retention6931objectives/run actualcrashchecks
separate; do notclaimharnessprovesthose. Stopif1000cannotfinishcaps,recordbudget
constraint andconcretebottleneck,noneed2k. No sourceorprocesspersonalactivation.

Review request: concrete safety/method flaws and cheaper adequate alternatives;
resourceboundadjustment usesmeasuredpilot,notunboundedbenchmark. No commands,
edits or seed searches in review.

High reviewc36025743568 succeeded exit0denied[],13763tokens,noedits/tests.
Codex accepts cheaper500-world gate (121500layouts) with1800s inner/1860s outer
watchdog beforeconsidering1000. Do NOT subsample layouts toclaimfull243coverage.
18query measurements are descriptive, notstablepopulationtailestimates.
Syntheticdata biases remain explicit. A watchdog kill mustretainprogress and
trigger audit/recovery; never reinterpret timeout aspassedworkload.
