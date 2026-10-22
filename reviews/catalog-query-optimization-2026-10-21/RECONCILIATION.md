# Query optimization review reconciliation

User approved PLAN.md with “Yes.” Codex owns integration and executed verification;
Gemini roles are independent static reviews, not test execution.

Plan review2d2445eb1f5a and patch reviews2367802e7a2e/09cf03dde7d5 all succeeded
with explicit gemini-3.8-flash-high/efforthigh, process exit0 and denied_actions=[].
Reported usage27794,22805, and the final reader review's saved usage respectively.
No worker changed files or ran tests. Exact results/pointers are in the three
WORKER*REVIEW.json files. Earlier preparation95ba7403fec7 failed the30KB context
cap before model execution; one narrower retry succeeded. No auth/quota bypass.

Accepted plan clarifications: module-level compiled strict ASCII fullmatch;
check point-list values rather than dictionary truthiness; isolate the query-local
top-level row on the empty-witness path. Public apply_witnesses keeps its copying
contract. Public index validators stay independently strict. Private selection is
used only after full request/index/content validation in the reader.

Rejected the plan review's specific claim that _rank inserts sort keys into input
layouts. Actual source constructs separate candidate dictionaries, and the saved
81-layout probe confirms inputs unchanged. A shallow copy isolates mappings; it
does not generally protect nested mutable values. Safety here depends on query-
local source objects, read-only scoring and result-cache serialization before
return. Cold/warm nested response mutation tests pass.

The first patch reviewer suggested an outside-layout fine-witness comparison;
that is already the explicit forced-copy reference case in the new regression.
Added unsupported request input types to the strict public/legacy checks. Existing
zero-row bitmap tests cover empty indexes; the publisher emits nonempty leaf
chunks, so an invalid empty leaf is not fabricated as a valid production case.

The initial optimized concurrent gate failed and remains preserved. Post-change
profiling exposed40500 identical per-seed world-ID derivations for500 seeds and
81000 layout-ID derivations for40500 rows. The small reader addendum consolidates
only those duplicates within the same approved file and validation architecture.
It does not introduce a cross-read cache or a new trust flag. Membership and
world-ID equality remain unconditional per row; the fixed header/seed derivation
is reused only inside one iterator. Strict unpack_summary still verifies the
layout identity. A no-index corrupted-ID regression and67 reader/oracle/accuracy
checks pass. Final reader review09cf03dde7d5 found no blocker in these invariants.

Review statements about all metadata corruption being caught refer to the full
pipeline: artifact checksums and snapshot/content/member bindings plus strict
decoding, not an assertion that unpack_summary alone detects every semantically
consistent forged record. Failed capacity is not waived by a favorable code review.

No timeout, active/admission limit, schema, extraction, predictor, scoring or
evidence-policy change is part of this patch. FOLLOWUP_PLAN.md is an unapproved
process-serving fallback; no such processes or implementation have been created.
