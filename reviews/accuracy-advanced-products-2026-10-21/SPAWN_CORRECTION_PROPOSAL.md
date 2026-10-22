# Low-cost world-spawn correction — approval proposal

Status: approved, implemented, validated and adopted locally on 2026-10-21.
See [RELEASE_REPORT.md](RELEASE_REPORT.md): 124 distinct Bedrock reference controls
matched and 222 catalog worlds migrated. The proposal below preserves the evidence
and scope presented before approval; its pre-implementation statements are historical.

## Cause and measured evidence

`vendor/cubiomes-bedrock/finders.c` performs the fitness search at2048/512 then
512/32 steps. Its internal findFittestPos then moves the found X/Z to the center
of its chunk: `(coordinate & ~15) + 8`. The chunk-center result is what the current
public helper emits. The raw fitness-search result matches the retained actual
Bedrock default-world reference instead. This hypothesis was tested before any
coordinate fitting; no new thresholds or random-seed tuning were used.

Isolated external diagnostic includes the current actual finders.c in one
translation unit and calls its same static calcFitness/findFittest kernels. It
omits only the final chunk-centering step, leaving those vendor sources unchanged.

| Evidence set | Distinct seeds | Raw fitness result exact X/Z | Existing estimate exact X/Z |
|---|---:|---:|---:|
| Earlier predetermined BDS1.26.52.3 cohort |108|108|0|
| Independent archived eight-world accuracy pilot |8|8|0|

The second eight seeds are disjoint from the108 and all match both Script API
default spawn and independently saved level.dat. Raw method median3.33ms on this
local diagnostic, compared with earlier~3.83ms estimator measurement under different
host conditions; this is not a controlled speedup claim. It performs the same
fitness search with fewer final operations, not terrain generation or block reads.

Artifacts/protocol, current source SHA, build/run outputs and per-seed comparisons:
`~/.local/share/antigravity-worker-mcp/accuracy-cheap-spawn-axubexla/`.
The108 native-vs-game error offsets previously had49 distinct values; an arbitrary
constant correction cannot explain these results. Current finders.c SHA256:
df15ccffd1d806bf702a770a483bff71d1eaeed6f76e229929551ea48c33f152.

### Additional planning validation

An interleaved same-compiler/same116seed local comparison now records580 calls
per method. Median: raw3.193ms versus current3.1985ms; p95: raw3.749ms versus
current3.786ms. Every output matches the original diagnostic. This shows no
material added cost in this bounded serial test, not a fleet speedup or proof of
the not-yet-built production helper. See SPAWN_PAIRED_COST_AUDIT.json; reproduction
source/protocol/results are under the external artifact root's paired-cost-audit/.

The eight fresh signed seeds and exact observation/resource protocol are frozen
in FRESH_SPAWN_CONTROL_PROTOCOL.json, SHA256
e71ac72232920056ca2ba5ccfcf4dc3bbf0db8afac1ad053788c69871b4d3d99.
They are disjoint from all116 prior controls. No fresh BDS worlds were executed;
implementation and game validation still await the requested user approval.

## Smallest proposed implementation

1. Modify only the separate helper's embedded C in
   `scripts/build_spawn_estimator.py`, not the vendor or either loaded engine.
   Include the existing finders.c in that translation unit; call the same current
   static fitness/search kernels without chunk centering. Exclude finders.c from
   the separate link-unit list to avoid duplicate symbols, but retain its hash in
   the build input manifest. The wrapper is a few calls, not another noise/search
   implementation. Pin modelMC_26_50; no other-version claim.
2. Preserve canonical signed64 input, repeated-output check, source/build manifest,
   timeout, output limits and provider semantics. Name it a predicted world-spawn
   reference; do not relabel predictions as per-world game observations or claim
   initial-player landing, usableY or safety. Its new executable hash supplies
   distinct evidence identity; both existing native engines and their sources
   remain unchanged.
3. Add a real compiled-helper evidence replay against all116 retained worlds,
   including archive checksums and independent level.dat/API identities. Existing
   mocked builder/adapter tests remain supporting tests, not the accuracy proof.
4. Freeze8 further signed seeds not in either old set before running BDS. One
   disposable BDS at a time,2CPU/2GiB,300s/world,1,200s total including setup/save/
   copies/cleanup,1GiB owned output, no players or terrain scans. Read default
   spawn at load and after ticks20/40; independently decode saved level.dat. Keep
   failures and every mismatch. A mismatch reopens causal investigation; no refit.
5. Measure old/new helpers in interleaved runs over the same seeds/compiler/input
   order, using repeated bounded batches. Verify new median and tail do not show
   a material cost increase; no billion-seed throughput claim.

## Catalog adoption must be explicit and source-bound

Build into a new external path, never overwrite the installed estimator. The
helper executable is included in automation configuration/policy identity, so
do not replace a pin inside an old configured root or relabel old anchor evidence.

Use a new policy workspace while keeping old snapshots/history/links readable.
Reuse the same222 worlds' absolute-coordinate structure/biome inventories and
existing Realm evaluations; only replace the estimated anchor with new helper
evidence, derive its three borders and projected Nether reference, and recompute
product memberships/summaries. Old refinements remain facts at absolute coordinates;
out-of-scope or incomplete coverage remains pending. Do not trigger fresh native
world searches because an import helper omits/misreads an existing evaluation.

Existing import code appends spawn only when absent: simply running it with a new
helper would incorrectly keep old anchors. The migration therefore requires one
explicit bounded re-anchor path using existing store/ledger/publisher methods,
with old-input digest/new-helper pin/checkpoint and unique-world checks. No new
database schema or generic migration framework. Preserve observed anchors, personal
Top50/checkpoints, calibrated scores and historical results exactly.

Allow one600-second migration allocation, one thread/4GiB/2GiB new output, resuming
from durable progress only after an explicit new allocation if needed. Stage a
separate root; compare all saved structure/biome facts and Realm evaluations before
adoption. Do not silently retain old estimated-mode summaries or product caches.
Publish a new immutable snapshot and adopt the catalog backend only when idle;
personal backend/binaries remain running unchanged. No new seed campaign.

## Delegation, checks and acceptance

Codex owns protocol, actual BDS runs, migration and final source/policy adoption.
One Gemini High worker independently critiques this exact plan before user
approval. After approval, helper/tests and migration correctness review can be
independent with disjoint ownership; no worker touches the primary native engines.

Acceptance: original116world replay plus8fresh held-out controls match actual
world-reference X/Z with failures retained; source/build pins correct; no added
terrain/physical-census work; comparable helper timings; all222 worlds re-anchored
exactly once; unchanged absolute facts/Realm results and old snapshots; independent
raw-coordinate summary/filter/membership oracle on changed anchors for all three
borders and Nether projection; affected Python/HTTP/Node/UI/build checks pass.
Unknowns stay unknown. UI keeps honest world-reference/prediction wording.

This does not assert all Minecraft versions/seeds are mathematically proved or
that player landing equals the reference. A finite zero-mismatch cohort supports
this build-specific correction. Estimated mode remains prediction-based. Any
new causal mechanism, model version or current-source identity mismatch stops
adoption rather than weakening checks.

Complexity: medium overall because provenance/migration matters even though the
algorithm adjustment is tiny. The direct requested terrain-card removal is a
separate routine change and does not wait for approval of this predictor stage.

## Reconciled Gemini High critique

Worker1521fe97f525 succeeded with gemini-3.8-flash-high / effort high, exit0,
nonempty response, denied_actions[], no edits/tests,21,172 reported total tokens.
It supports the finite build-specific evidence and helper-only reuse, and stresses
manifest inclusion of finders.c, boundary-membership oracle, exact222-world
preservation and aborting adoption on fresh-control failures. These gates are
explicit requirements above, not optional post-release checks. Include system
headers before the vendor C unit and compile the helper with warning diagnostics;
inspect actual warnings rather than changing unrelated vendor code.

The reviewer called its recommendation "approved for execution"; this is a peer
opinion, not user approval. Significant implementation still waits for the user.
Its illustrative "up to15 blocks" anchor shift is not an adopted bound: compute
the actual old/new X/Z delta and all border/distance differences from raw facts.
The chunk-centering displacement is not a certified error bound to Bedrock or
to player landing. No duplicate fitness/noise implementation is accepted.
