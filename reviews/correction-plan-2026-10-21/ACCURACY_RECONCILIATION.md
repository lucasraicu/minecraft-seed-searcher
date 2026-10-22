# Practical accuracy implementation — independent review reconciliation

The user approved the first/practical option after High feasibility/architecture
reviews a47b85533a04 and edcb454d9672. Exact initial-player landing and physical
instance census remain gated. This is not a declaration of universal accuracy.

Gemini High coding jobs edba7537105a (denied required write, empty provider response)
and a1d5ca44cb16 (timeout) failed. No failed patch was accepted. Codex authored the
compact provider/matrix implementation after inspecting partial work and ran checks.
Core review91b695d759a5 succeeded (24777 reported tokens; no edits/tests). Its empty
clipped-scope finding was fixed by rejecting empty scopes, with a regression.
Pilot reviewe834caf939aa timed out; one narrower reviewb6771149e2cb succeeded
(31862 tokens). That was static observer review, not independent runtime testing.
Codex ran and inspected the actual game jobs, identities, settings, saves and cleanup.

## Final core review c9a347812d01

Succeeded, exit0, denied_actions=[],46502 reported tokens; no edits/tests.
Codex reconciled each finding against code and meaningful checks:

1. **Coarse absence proposal rejected.** The complete bits describe the evaluated
Y63/stride64 lattice. They do not prove every block absent. Converting a missing
witness plus complete lattice into impossible would incorrectly remove potential
small patches. The versioned query keeps these worlds unresolved, separately from
matches. Tests include sparse missing witness and a real dense game tile with99
taiga points absent from that tile's one coarse sample.
2. **Positive OR improvement accepted.** The new evidence policy lets a positive
witness satisfy A-or-B while B's coverage is unknown. An explicit opt-in scorer
flag preserves legacy v1 behavior. Required and preferred/distance behavior use
positive witnesses; absence is not inferred. A real-source service regression
covers partial OR coverage, fine witness recovery, cached result immutability and
unchanged legacy contracts.
3. **Capacity explanation corrected.** The measured failing case was500 WORLDS
with EIGHT simultaneous requests, not500 simultaneous requests. It used the old
v1 path without accuracy bundles. Accuracy bundle parsing cannot explain that
failure. The failure stays recorded: two10s timeouts and sixbusy responses.
Integrity checks stay before cache reuse; moving the cache ahead of verification
would weaken corruption checks. Current accuracy cache timings are measured
separately; no production SLA is inferred.
4. **Origin leak claim rejected.** Origin is intentionally one of the81 Recommended
candidates. All v1 grid layouts fit the declared envelope, and _rank deduplicates
worlds before TopK. Rehearsal matched200 unique worlds in both modes across all
three borders. Excluding Origin would change the approved player semantics.
5. **Redundant cold bundle read fixed.** The validated bundle is now returned by
one binding helper and reused.
6. **Cursor-expiration claim rejected.** _page calls the shared service._decode,
which already validates expiry. A new cached accuracy-query test rejects an
expired signed cursor. Request/generation/snapshot/page-size binding is preserved.

## Final UI review547e3de479d3

Succeeded, exit0, denied_actions=[],29056 reported tokens; static supplied-excerpt
review only, no edits/tests or interactive browser verification. Accepted: dedup
anchor modes/key by mode, aria-pressed selection state, and independent favorites
storage-error reporting. Rejected suggested missing-border fallback: the typed
backend/scorer always emits border_side; silently supplying the currently selected
border would hide malformed saved-layout metadata. Strict favorite validation stays.
A real-hook harness checks generation/version binding, unavailable-mode reset,
unknown candidate separation, blocked storage, spawn semantics and new-mode favorites.

## Evidence limits

Twenty types have positive point membership in scoped Beta copies. Stronghold has
a default-game located-reference route and actual generated brick witnesses, but
no positive membership witness in this sample. No point or locate method is a
physical-instance census. The camp gap was a verifier namespace error: the generic
structure-set identifier is not the biome-specific structure identifier. Default
same-world controls and an independent second seed establish the corrected route.
Temple subtypes use exact observed membership strings, not grouped temple locate.

Stored-ID/name associations in the new pilot are scoped measured associations,
not independently proved global registry identity. Raw missing records stay unknown.
A separate owned-copy persistence repair recovered the missing Nether records and
preserved its original source. All source-backed raw structure gates remain raw.
New provider namespaces cannot share game-run negative proofs merely by seed/build.
