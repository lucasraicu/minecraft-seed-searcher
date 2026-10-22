# Exact block-Y correction — proposed, deferred until audit finishes

User decision: finish the audit before changing the predictor. The proposal and
prototype below remain evidence for the final combined recommendation. No native
implementation or publication is authorized by that ordering decision.

The five-world pilot found three BDS-exact village references rejected by the
current model, including one blind seed. Their immutable cases are 2-68,16-70,
16-71 in manifest bbc14d21fba0455ed8f7cfe66099f34b6734575dfb7d8ffbcb00337eced72f1c.
An isolated prototype restores all three while preserving 51 earlier positives
and the two earlier negative controls. This is evidence of over-rejection, not a
physical village census. The original predictions remain frozen.

Objective: correct the Y coordinate used by the MC_26_50 preliminary structure
biome check. BDS fallback rounds X/Z to quart coordinates but retains exact block
Y. The present helper rounds Y down too, sampling two blocks below each intended
village corner. Preserve the full 3D corner volume, biome allowlist and height
provider; do not introduce seed exceptions, thresholds or extra exclusions.

Changes, in order:

1. Codex adds compact hashed regressions bound to raw BDS reports and console
   evidence for these three cases; retain historical failures and controls.
2. In vendor/cubiomes-bedrock/biomenoise.c/h expose an exact-block-Y entry point
   through a private sampler core supporting fractional quart Y. Keep the existing
   integer-quart API and its numerical operations unchanged at defined inputs.
   Preserve optional climate parameters, search cache and sampling flags.
3. In finders.c use this entry point only in the existing MC_26_50 preliminary
   helper, including its center biome. Older models, dimensions and ordinary
   block/grid biome selection remain unchanged. Outpost height is a multiple of
   eight, so its output should be invariant; explicitly test that.
4. Tests: old/new integer-quart equivalence across representative seeds, X/Z/Y,
   versions and flags, including climate parameters; exact negative/fractional Y;
   three new positives, 51 old positives, two existing negative controls; existing
   8320 stored/330 direct/3920 raw-node cases and actual isolated optimized CFFI.
   Compare the remaining frozen worlds as held-out evidence without changing
   their pre-fix predictions. No primary extension replacement or service restart.
5. Only if the evidence supports it, prepare a separate immutable same-seed
   catalog refresh with provenance/query checks and retained historical snapshots.
   No automatic publication under the audit-only approval.

Gemini High review f68d4043ea1a succeeded, exit0, denied_actions=[], 25,332 reported
tokens; no edits/tests. Codex accepts the exact-Y causal evidence, full-cube
requirement and explicit parity checks. Qualified/rejected suggestions:

- Integer API compatibility must be measured, not assumed merely from a wrapper.
- Float-order differences are a residual risk; the worker's proposed float formula
  is not a proven complete transcription of the BDS spline path. Do not combine
  that broader numerical change with this narrow coordinate correction.
- Do not broaden to unverified older versions. The current preliminary helper is
  already version-gated; changing earlier models would be a separate project.
- The worker's claim that BDS clamps to int16 bounds does not establish the exact
  world-edge loop behavior. Keep existing bounds unchanged; test them explicitly.
- More physical absence controls would strengthen inference, but another locate
  reference is not such a control. Preserve unknowns and investigate discrepant
  retained/rejected cases rather than declaring the rest absent.
- Fresh-world cache/blending behavior remains a documented scope limit. No
  general guarantee for upgraded, blended or nondefault worlds.

Ownership: Codex owns the three native files, new regression tests/fixtures and
isolated validation; the High worker provides independent critique only. Work is
small-to-moderate, about 30–60 minutes plus held-out game validation. CPU-only,
no additional game budgets or seed search. Acceptance is all scoped checks pass,
new counterexamples restored, prior negatives retained and no unexplained parity
changes. If another cause appears, stop dependent publication and report it.
