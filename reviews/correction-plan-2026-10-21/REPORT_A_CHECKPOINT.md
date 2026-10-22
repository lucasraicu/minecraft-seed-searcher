# Correction plan — implementation checkpoint

The user approved NEXT_FIX_PLAN.md after completion of the generalization audit.
Section A is implemented and independently checked. Section B source diagnosis is
still active; the full goal is not yet declared complete. Deployment and catalog
publication remain separate steps under section C.

## Implemented corrections

- Backend construction and handle use now reject stale compiled sources before
  native computation. Raw layout/sweep and biome inventory entry points are also
  guarded. Successful validation is cached by process and loaded ffi/lib identity,
  with strong references, serialized revalidation and fork reset. Explicit
  native_runtime() preflight freshly validates at job boundaries and invalidates
  failures. The cache does not watch subsequent source edits during a running job.
  Wheels without source trees check embedded digest syntax, not unavailable source
  provenance. No implicit rebuild or permission bypass occurs.
- Importing predictor_storage_probe no longer changes runtime import precedence.
  Direct CLI execution appends its source fallback only in __main__.
- The MC_26_50 preliminary village/outpost helper samples exact block Y and keeps
  its full 3D bounds, biome allowlist, height provider and center semantics. Older
  models and ordinary biome sampling retain the integer-quart API. The private
  core accepts block-space depth; the old API performs its original int Y*4 before
  conversion, preserving -fwrapv edges as well as normal world coordinates. This
  strengthens the proposed fractional-quart core without broadening the rule.

## Verification performed by Codex

- 134 focused checks pass (11.00s), plus 12 existing backend checks on the new
  isolated optimized runtime (0.14s). One expected Python deprecation warning comes
  from deliberately testing fork while another thread holds the validation lock.
- 98,000 old/new integer sampler vectors preserve biome, climate vector and cache;
  56 additional integer extremes preserve wrapping behavior across eight flags.
- All14 BDS-exact rejected village references are retained. The original prototype
  was frozen after three cases; eleven later BDS witnesses remained held out from
  that initial proposal. The earlier51 positive and two negative controls remain.
- 916 frozen structure checks exercise older models and current outposts, with
  current BDS-exact village positives retained. The optimized CFFI separately
  preserves all95 selected current outpost cases.
- New isolated O3 CFFI reproduces all3,411 frozen biome predictions and preserves
  8,320 stored-point and330 direct-game controls. The independently compiled
  native checks also preserve3,920 raw quart nodes. Existing biome disagreements
  remain disagreements; matching old predictions does not fix them.
- A real helper-first import uses the selected isolated extension. The actual
  stale primary extension is blocked in a fresh process. First preflight measured
  10.2ms; a10,000-call local sample measured0.545microseconds per cached guard.
  This is guard overhead, not a seed-search throughput benchmark.

Final native source digest:
`e37a49f49ef2bd0ec083183443f49a656a4beb367841b240a87629e5604eb5a1`.
Optimized serial extension digest:
`3d1fad92165f3cc89fd5a9292e0f97b5162d7dec5fc75a9206f8a52150b2b96d`.
Raw/derived evidence is bound in ARTIFACTS.json and optimized-*.json.

## Worker contributions and reconciliation

All worker roles used gemini-3.8-flash-high with effort high through MCP.
Runtime coding task480ff86c526c timed out after480s, with no validated result.
Codex inspected but did not integrate its partial work; cache ID reuse, races,
fork locking and test-module pollution required a different implementation.
Two preceding requests were rejected by executable-allowlist validation before
any job was created; the corrected python3 request used the supported policy.

Native review82f50687caad succeeded, exit0, denied[],23,603 tokens. Its broad
MC1.18+ wording was wrong: the changed helper is MC_26_50 only. Its claims of
12 test suites and warning-free compilation were not evidence; there were12 tests
and inherited compiler warnings. Its integer-promotion claim overlooked the old
int multiply. Codex corrected that edge, verified56 extra vectors and obtained
final reviewc01d361fb591 (success, exit0, denied[],13,265 tokens), no blocker.

Runtime review65abc6114967 timed out without a result. One narrower High review,
7e9620db1ff3, succeeded (exit0, denied[],14,886 tokens), no blocker under the stated
job-boundary contract. Its phrase native_runtime(force=True) is not an API:
native_runtime() takes no argument and calls fresh validation by default.
Reviewers ran no tests; the checks above are Codex's independent results.

Source worker0971ab8e1019 succeeded (exit0, denied[],34,825 tokens). It derives
city/bastion argument flow; its inferred parameter meanings remain subject to
actual callee inspection. See SOURCE_INVESTIGATION.md for subsequent evidence.

Only six preexisting source files differ from the509-file stage baseline:
the three approved native files, backend.py, realm/native_identity.py and
predictor_storage_probe.py. New tests and frozen reference fixtures are additive.
The primary extensions, personal server and catalog have not been activated or
rewritten. No new BDS process or seed sweep was started for this checkpoint.
