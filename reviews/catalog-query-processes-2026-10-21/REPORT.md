# Two-process catalog serving and OpenMP restoration

Completed the user-approved CPU process plan and existing OpenMP restoration on
2026-10-21. No new GPU implementation, database engine, predictor algorithm or
natural seed campaign. This report supersedes the earlier unresolved concurrency
gate; its failed baseline measurements remain retained.

## Catalog result

The standalone catalog preview now starts two owned `spawn` processes before
accepting traffic. Optional in-process embedding remains available. Query children
execute the existing exact scorer with request-scoped SQLite connections, bounded
caches and an idle-worker affinity hint. Parent admission stays four, execution
stays two, and the absolute ten-second allowance includes queue and IPC time.
The single queue-wait allowance remains at most two seconds. Results, scoring,
uncertainty, immutable membership checks and signed pagination are preserved.

IPC is framed JSON with duplicate-key/nonfinite/schema/job/generation validation;
both reads and writes have deadlines. Input/output caps are 1 MiB/4 MiB. A
conservative current-schema reply envelope is 2,068,213 bytes, including 50 rows,
12 contributions, nine alternatives, fine witnesses, worst-case escaped identity
strings, 50 unresolved candidates and an oversized cursor reserve. Unexpected
oversize responses fail explicitly. This bound needs revisiting for new schemas.

Worker failures produce explicit errors and do not replay a job. Failed workers
are quarantined before bounded cleanup/replacement. Three failures within five
minutes exhaust recovery until explicit reinitialization. Healthy process leases
prevent double dispatch during degraded capacity. Parent death is watched by
children; normal shutdown closes the pool. No shell/search/extraction dispatch API
was added. Application read-only behavior is not an OS sandbox.

Measured using existing disposable corpora, fresh application caches and unflushed
OS filesystem caches:

| Check | Result |
| --- | --- |
| 500 fabricated worlds / 121,500 layouts / 18 cold queries | All exact full ordered pagination matches frozen unfiltered enumeration; maximum 7.517 s |
| Previously failing admitted query pair 5/10 | Both 200: 6.760 / 3.938 s |
| Two broad Recommended queries 3/15 | Both 200: 7.680 / 7.655 s |
| Eight distinct cold HTTP requests | Two exact 200, six explicit 429, zero timeout 503 |
| 500-world immediate warm queries | Median 0.0271 s; provisional 0.15 s median budget passes |
| Existing 200-world accuracy corpus | Four anchor modes × three borders, 200-world unique pagination and 18 provider-specific scope checks pass |
| 200-world accuracy warm queries | Median 0.1116 s, maximum 0.1217 s; provisional 0.25 s budget passes |
| Separate heavy-pair CPU attribution | 15.31 child CPU seconds in 7.683 wall seconds: 199.27% aggregate CPU, both exact 200 |
| Worker startup | Live preview 0.264 s, separate CPU test 0.229 s; not included in cold request times |
| Sampled aggregate memory | 263.4 MB (500-world suite), 321.9 MB (accuracy suite), 277.2 MB (CPU pair), all below 2 GiB cap |

Memory sampling includes benchmark parent, descendants and monitor at 100 ms;
these are sampled peaks, not a formal worst-case bound. The third descendant is
Python's resource tracker, not a third query worker. Two worker caches each keep
the existing 64 MiB serialized allowance; Python overhead is additional. HTTP
latency minus child-reported query time includes framing, serialization, scheduling
and loopback HTTP; it is not a pure IPC microbenchmark. Evidence has the actual
per-case timings. Measurements do not establish production capacity at arbitrary
scale or during a simultaneous saturated sweep.

Actual tests: **39 passed in 12.64 s**, covering actual one/two-worker queries,
cache isolation/affinity, cross-worker and recovered cursors, invalid/expired
requests, positive fine-biome OR witnesses, retained unknowns, warm corruption,
blocked IPC writes, worker SIGKILL, bounded restarts, degraded leases, malformed
replies/frames, startup failure and idle/busy parent-death cleanup. Two final
cleanup checks also reran after tightening owned-PID cleanup identity. An initial
test command named a nonexistent test file; it did not run tests, and the corrected
command is the passing evidence. The first test setup also encountered missing
psutil; tests use stdlib process inspection rather than adding a dependency.

## OpenMP result

Source support had survived. The primary general extension was serial, while old
private sweep extensions declared OpenMP but had stale source manifests. Existing
preflight correctly prevented those stale binaries from becoming current jobs.

Both current-source extensions were built through **absolute isolated scripts and
explicit isolated working directories/PYTHONPATH**, then validated. No native
build ran in the primary repository. Corrected source fingerprint:
`72694b1420170b4582358eef577cc252c11e138daec817bbf97d4af68e645c1a`.

OpenMP forms actual teams of **1, 2, 4 and 34 threads**. Every complete semantic
record matches across these teams and the corrected serial runtime: 64 declared
synthetic worlds per setting, plus 220 Overworld/Nether biome point values on two
existing regression seeds. An independent Python reconstruction also matches.
An additional 1,280 biome values use 320 points per call, exceeding the native
parallel threshold of256; the actual point-parallel branch matches serial at
1/2/4/34 threads, with independent scalar spot checks.
These are bounded parity checks, not a new seed campaign, broad performance
benchmark or universal game-accuracy proof. The tiny native fixture kernel took
41.0 / 20.9 / 11.0 / 17.9 ms at 1 / 2 / 4 / 34 threads respectively; this does not
justify choosing 34 threads for every workload.

Installed on-disk artifacts after exactness checks:

- `_native.abi3.so`: `c18610aa8008a27eb130808b18d69099d023771182b55b8c731054883d765f63`.
- `_blueprint_batch.abi3.so` and fresh private sweep library:
  `3fbb286e4f06a4726e3c1e7216a5aad4d30f2abc6b0bf7b97532bf085b372687`.
- New private directory:
  `runs/dynamic-baseline-2048/native-corrected-openmp-2026-10-21`.
- Pinned libomp: `af4f16ce7fb34f8e444d328b105adead0b655768e32aadbf438972d8e79f92f6`.

Old primary artifacts were backed up externally before atomic replacement. All
historical private runtime directories remain intact. The server selector prefers
the fresh compatible private build; explicit overrides and saved resume identities
remain authoritative. A fresh primary process passes source/runtime preflight and
selects this build. **The already running personal server60144 was not restarted
and retains its previously loaded runtime. It needs a later explicit restart to
adopt the restored artifacts; there was no hot reload or new sweep.**

Native guard and independent center/refinement checks: **23 passed in 5.04 s**.
The two excluded existing cases were the real-world persistence run and a test
whose fixture builds serial; actual OpenMP team parity is verified separately.
The fork-reset regression emits Python's existing multi-threaded-fork warning.
The linker warns the pinned libomp target15.8 exceeds the extension target10.13;
local import/execution succeeds, but these artifacts are machine-local, not a
portable macOS release. No algorithms, source fingerprints or scheduling rules
were weakened to obtain a pass.

## Reviews and preservation

Gemini High source audit **27f46685a8b3** and pool lifecycle review **d314029b6dff**
succeeded, exit0, denied_actions=[], no edits/tests. Codex independently inspected
the patch and ran all checks. Full pool review45a388539895 timed out at180s; one
narrow controlled retry produced d314029b6dff. Activation critique d620fc4fb30f
returned a nonempty High response with exit0/denied[], but the bridge marked it
failed because the required-response substring was specified too broadly. It is
retained as advisory content, **not a successful worker task**. Its no-blocker
opinion does not substitute for actual artifact/selector/preflight tests. Its
assertion that combined-load latency necessarily fails, and suggested thread32
budget, are unmeasured: Codex records possible contention, not a guaranteed result.

Catalog preview PID77098, workers77100/77101, port3001 is live; Vite5173 proxies it.
Both surfaces pass query, detail, anchor-role, malformed-scope and research-product
checks. All **2,494** existing non-SQLite catalog files retain their hashes;
snapshot `18ca9deb3da9ed0d9dec553cf1447d3ffbf9ac2ed003d1dccc5a0d5af336ba93`
and accuracy generation
`9d474e733f4b2bbe4b663bd76e55e8cac9a564ecd55a6622a054e5a55592051f`
are unchanged. The personal PID/start time, completed run and full candidate data
are preserved. Its preexisting `discoveredAt` display field uses the current clock
on every read (`server.py`); only that transient field is excluded from comparison.
Primary binary preservation was proved through the catalog phase; its subsequent
intentional OpenMP replacement is separately recorded and recoverable.

No reset/stash/clean/commit/push/merge, new database, GPU job, billing activation or
browser automation. Interactive browser QA remains waived. No frontend source
changed in this task; prior automated UI checks remain applicable, with fresh live
API/proxy verification. Evidence bindings and compact results accompany this file;
larger raw outputs, scripts and original binaries are retained under the two
external directories listed in ARTIFACTS.json.
