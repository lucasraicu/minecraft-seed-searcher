# Direct village evidence audit — 2026-10-20

User authorized a direct Bedrock check after questioning the Rare preview count.
No application source, native binary, serving dataset or UI wording was changed.

## Result

Seed `-3509659830737203357`, Origin-centered closed circle radius2,000 blocks:
28 distinct biome-viable predictions; **27 exact BDS locate-coordinate matches**.
At `(-296,-312)`, BDS instead returned `(-888,136)`. All25 additional queries
in a +/-128-block neighborhood returned that other location. This is a reproducible
disagreement, not an established root cause or proof of a physical village absence.
64 independent grid queries found no new in-circle locations beyond the27 matches.
The grid is not an exhaustive census. Neither28 nor27 is certified as the complete
physical village count. Generated blocks/buildings were not inspected.

The older80/80 village reference positions still match the current native engine
exactly. Their original source explicitly says third-party UI predictions, not
in-game observations. Those controls support marker correspondence but do not
establish complete game-world recall or validate this new seed's full count.

## Method and controls

Pinned BDS1.26.52.3 image SHA256
`cf479afd0ab8a8bb095f7aa71fd42064cf5ba7aff6c8a8f4f5503aac826511d8`.
Script API observed the exact requested signed world.seed in fresh default worlds.
Each query was `execute positioned X 100 Z run locate structure minecraft:village false`.
28 predicted positions +64 grid points +25 follow-up queries =117 successful queries.
Two successful bounded runs took8.93s and5.59s including startup/shutdown, respectively;
these are audit runtimes, not general throughput benchmarks. First harness attempt
received the first correct locate result but timed out waiting for a silent `say`
marker; corrected harness waits for one locate response before issuing the next.
All three disposable containers shut down cleanly and were removed.
Caps:4CPU,6GiB,900seconds/run,100queries/run,8GiB output; no host ports published.
Original Sweep and catalog services were preserved. No Gemini worker ran BDS;
Codex executed and independently parsed all117 results.

## Shared product implications

`products.py` currently defines one prediction evidence label; the React preview
component uses predicted starts for all five live Rare research lists.16 Presets
and22 named Rare records are gated, not live verified seed matches. Personalized
results also need the same feature-specific evidence policy as they evolve.
Do not globally replace predicted counts with verified counts. Observed evidence
must bind world, feature, exact build/settings, coordinate, method and scope.
A village-only audit cannot certify trial chambers, portals, pyramids or shipwrecks.

## Reproduction evidence

Compact independently parsed results: [village-summary.json](village-summary.json).
Raw logs, scripts, controls, query responses and disposable world directories:
`~/.local/share/antigravity-worker-mcp/catalog-spawn-village-plan-20261020/`:
- `direct-6a7e09bcec9b/`: initial marker harness failure, clean cleanup.
- `direct-0badfe0d6d93/`:92 successful queries.
- `direct-0401a95e90fa/`:25 mismatch-neighborhood queries.
- `village-reference-recheck.json`:80 current-engine marker controls.

No gameplay/building-footprint observation or exhaustive census is claimed.
Next substantial implementation requires approval of the reviewed plan.

Independent Gemini High task `0c29cff8e16a` reviewed the inference and proposal;
Codex reconciliation and implementation scope are in [PLAN.md](PLAN.md).
The worker did not run the game checks or independently inspect raw files.
