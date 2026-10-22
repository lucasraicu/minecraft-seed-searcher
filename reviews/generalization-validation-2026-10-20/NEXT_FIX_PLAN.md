# Proposed next corrections — no implementation yet

User directed finishing the audit before changing the predictor. This proposal
follows the completed audit; it is not an inferred approval to implement, deploy,
rewrite the catalog or start another seed sweep. Significant implementation needs
the project AGENTS.md review/approval gate.

## A. Changes with direct evidence

1. Prevent stale native runtime use in direct Backend callers and diagnostic
   entry points. Audit evidence shows predictor_storage_probe prepended primarysrc
   before supplementary backend imports, silently selecting the old personal
   binary until explicit native_runtime() validation. Files:backend.py,
   realm/native_identity.py only if necessary, affected diagnostic entry points
   and focused tests. Validate before constructing/using a real native handle;
   do not hash the entire source tree for every searched seed. Prefer an explicit
   validated immutable runtime identity per worker/job and a clear cache/invalidation
   contract. Existing active personal process/binary stays untouched.
   Distinguish editable-source validation from installed-wheel identity when the
   source tree is absent; a process cache alone cannot detect later disk changes.
2. Implement the reviewed exact-block-Y preliminary village correction in
   vendor/cubiomes-bedrock/biomenoise.c/h and finders.c. Keep the existing integer
   quart API and mathematical operations at defined inputs, add an exact-block-Y
   entry point via a private fractional-quart core, and use it only in the existing
   MC_26_50 preliminary helper. Preserve full3D corner checks, height provider,
   allowlist, center ID behavior and version boundaries. Do not broaden float
   arithmetic or older-version behavior under this fix.

Codex owns integration and the three native files. A useful isolated Gemini High
coding worker could own only the Python runtime guard/tests; an independent High
reviewer evaluates the final native patch. No overlapping writable ownership,
new seed search or automatic publication. Reuse the current dirty baseline in
isolated snapshots and dependencies; never replace the primary loaded extensions.

Validation: stale-runtime regression must reproduce the actual import-order case
and fail before native work; verify validated runtime use after helper imports.
Measure/bound preflight overhead so it does not add per-seed source hashing.
For exactY:14 new BDS-exact positives,51 older positives, two established negative
controls,98000 integer-quart comparisons including climate vectors/cache/flags,
boundary/negative-coordinate cases and explicit outpost invariance. Separately
replay the frozen outpost structure cases separately from the biome observations;
3,411 biome points are not 3,411 outpost checks. Independently
build optimized CFFI in a NEW isolated directory. Preserve all3411 frozen block
predictions, existing8320stored/330direct/3920raw-node controls and supported
legacy models. Existing biome disagreements remain recorded; do not weaken tests
or claim this village-only correction fixes them.

Acceptance: stale binaries cannot silently supply new audited results; all
scoped parity checks pass;14 rejected reference counterexamples are restored
without losing old controls; no unexplained unrelated model changes. Complexity
moderate, roughly1–2hours including isolated builds/tests, subject to findings.

## B. Diagnose before changing other predictors

- Overworld cached ceiling: derive the chunk/volume bound from actual BDS source
  and saved data; distinguish raw procedural climate and cached runtime lookup.
  The observed Y95 bound belongs to one chunk. Do not hardcode it or clamp raw
  structure viability to a serialization artifact. Add independent boundary/height
  cases before promising arbitrary-Y game equivalence.
- Nether: derive Bedrock's real source/coordinate selection, test independent
  boundary/height cases, and compare seed-bit/coordinate hypotheses without fitted
  offsets. A copied Overworld8-grid change does not fix current failures. No model
  rewrite until a source-backed rule survives independent controls.
- Bastion/Ancient City: establish the Bedrock start-biome/check position rather
  than rejecting by an unproven variant-center or fixed-height sample. Preserve
  raw starts and viability/evidence separately in diagnostics. Test fortress
  interaction and candidate/reference/footprint differences. Do not globally
  allow basalt deltas or erase Deep Dark constraints merely from these witnesses.
- Temple subtypes, trial/trail/stronghold references and abandoned camps: keep
  the specific method gaps explicit. A feature promise may remain unavailable
  without discarding an otherwise useful seed. No absence/census/rare-density
  guarantee from these point methods.

These are bounded investigations, not preapproved speculative fixes. Concrete
mechanisms, file scope, resource bounds and held-out controls must be reviewed
before any consequential implementation. No reliable completion ETA for unknown
mechanisms is established by the current evidence.

## C. Integrate only after validation

Any justified extractor change needs a new identity and a separate immutable
same-cohort catalog refresh with summaries/index/query/recovery checks, preserved
historical snapshots and honest evidence rebinding. Personal-engine activation
requires controlled rebuild/restart after checking active work. Neither follows
automatically from this audit. No GPU or custom storage engine is required here.
