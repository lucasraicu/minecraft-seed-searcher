# Public automation: proposed product scope

Planning only, 2026-10-21. No production or predictor changes authorized by this document.
User requests full public automation, accepts the Pillar 1 direction, adds public
Nether filters and stronghold to Pillar 3, rejects arbitrary sliders/travel-only
geometry, and asks which Pillar 2/4 promises can avoid complex generated terrain.

## Evidence and meaning of difficulty

Inspected `catalog/products.py`, `structure_verification.py`, `summaries.py`,
`harvest_worker.py`, `realm/config.py`, the corrected public master plan and
correction/benchmark reports. Existing personal and public processes are preserved.
All 16 named presets and 22 named records are currently gated in products.py;
five Origin-centered research density products have executable rules. Offline
retention exists, but continuous admission/membership/reclamation is not connected.

- Easy: exact bounded geometry/count/ranking over available **predicted starts**.
  This is not an assertion that every predicted instance physically exists.
- Medium: new typed dimensions/features, targeted procedural biome refinement,
  explicit cluster rules, or bounded connected-component computation. These need
  code and held-out validation, but not terrain generation for every seed.
- Defer: the full current promise requires terrain, structure pieces, spawning,
  loading or portal behavior that our current observations cannot establish.
  Not impossible in principle; unsuitable for this inexpensive automated release.

All distances below are horizontal closed circles unless otherwise stated. A
model biome at a selected Y is not proof of walkable surface, an open cave, safety,
village subtype or contiguous physical landscape. Sparse 64-block samples miss
small patches. Small radii must be evaluated exactly, not rounded to 256/512/1024.
Estimated world spawn must be labeled estimated; observed world spawn is optional
scoped evidence, not a requirement to generate every catalog world. Neither means
exact first-player landing. Start distance is not footprint distance.

## Pillar 2: all sixteen presets

| Preset | Practical version | Difficulty / removed promise |
|---|---|---|
| Six-Pack | Six specified structure types within 300 Overworld blocks of estimated world spawn | Easy geometry |
| Loot Run | Ancient city + trial chamber within 200 OW blocks | Easy geometry |
| Mansion Village | Mansion + village within 300; optionally a separate plains biome witness | Easy without subtype; medium for plains witness. Actual plains-village subtype deferred |
| Triple Start | Village + shipwreck + ruined portal within 200 | Easy geometry |
| Temple Rush | Desert pyramid + ruined portal within 150 | Easy geometry |
| Nether Duo | Fortress + bastion within 200 Nether blocks of a declared nominal Nether reference | Medium integration; actual generated starter portal not promised |
| Cherry Blossom Haven | Cherry grove witness + village within 150 OW blocks | Medium refinement; remove proven plains-village subtype |
| Alpine Meadow | Meadow + cherry witnesses within 300 | Medium new meadow feature/refinement; flat high plateau/vistas deferred |
| Bamboo Temple | Bamboo jungle witness + jungle temple within 300 | Medium refinement |
| Frozen Frontier | Snowy biome witness + village + igloo + ice spikes witness + ruined portal within 300 | Medium exact biome subtype/refinement; snowy village architecture and basement not certified |
| Badlands & Desert | Badlands witness + desert pyramid + village + trail ruins within 300 | Medium refinement |
| Shipwreck Bay & Village | Rename to Village & Two Shipwrecks: village + at least two shipwrecks within 200 | Easy revised version; coastline/bay geometry deferred |
| Mushroom Haven | Rename to Mushroom & Monument: mushroom fields witness + monument within 300 | Medium revised version; biome touching footprint and safety deferred |
| Villagers & Pillagers | Village + outpost within 300, optionally plains witness | Easy revised version; true plains-village subtype deferred |
| Witch Next Door | Village + swamp hut within 200, optionally plains witness | Easy revised version; true plains-village subtype deferred |
| Safe Nether Outpost | Rename to Warped Forest & Bastion: witness + bastion within 200 Nether blocks of nominal reference | Medium integration/refinement; no hostile-free or safe terrain claim |

Definitions with weakened promises need a new product revision, accurate labels
and predicates; do not silently activate an old stronger claim. Preserve original
definitions gated if the corresponding renamed variant is launched. Biome claims
say which height/provider was checked, not that the base is physically in a biome.
Proposed ranking: minimize the farthest required feature/witness squared distance,
then sum of required squared distances, then world ID ascending; for >=2 shipwrecks
include the nearest two distinct predicted starts. Require all witnesses against
the same reference. Proposed capacity Top250 unique worlds per preset, not an
admission minimum or evidence guarantee. Validate tiny boundary cases exactly.

## Pillar 4: all twenty-two named records

Proposed simple density scope is closed 2,000 OW blocks around estimated world
spawn, or closed 500 Nether blocks around its nominal Nether reference. These
are proposed product definitions, not reinterpretations of the existing Origin
research lists. Count positive predicted starts; rank count descending/world ID
ascending. Search population/frontier and predictor revision are mandatory.

| Record | Practical candidate version | Difficulty / limit |
|---|---|---|
| Megacity | Most villages in declared OW scope | Easy |
| Trial Gauntlet | Most trial chambers in same OW scope | Easy once scope frozen |
| Deep Dark Metropolis | Most ancient cities in same OW scope | Easy count; cave/deepslate cluster scenery deferred |
| Outpost Siege | Most outposts in same OW scope | Easy |
| Nether Fortress Empire | Most fortresses in declared Nether scope | Medium dimension integration |
| Bastion Fleet | Most bastions in declared Nether scope | Medium integration; define as density rather than physical overlap |
| Ruined Kingdom | Most ruined portals in OW scope | Easy |
| Desert Dynasty | Most desert pyramids in OW scope | Easy |
| Sunken Armada | Most shipwrecks in OW scope | Easy revised density; coastal/ocean-floor terrain promise deferred |
| 0m Mansion Spawn | Rename Mansion Near Spawn: start <=50 from estimated world spawn; rank by distance | Easy revised proximity; no literal 0m/touching claim |
| 0m Ancient City Spawn | Rename Ancient City Near Spawn: projected start <=50 from estimated world spawn | Easy revised proximity; not directly above a Y=-51 footprint |
| 0m Monument Spawn | Rename Monument Near Spawn: start <=50 | Easy revised proximity; no sandbar/facing claim |
| Quadruple Overlap | Rename Four-Type Structure Cluster: four different OW structure types, maximum of all six pair distances <=100; each within300 of estimated spawn | Medium cluster search; no physical collision claim |
| Direct-Drop Portal | None that preserves the advertised inside-room landing | Defer actual portal linking, room/piece and terrain simulation |
| Quad Witch Hut | Rename Four-Hut Cluster: four distinct hut starts inside a horizontal128-radius circle about a computed candidate center | Medium geometric candidate; not a working farm or 3D AFK sphere guarantee |
| Double/Triple Monument Farm | Rename Double/Triple Monument Cluster with explicitly declared horizontal128-radius candidate-center circle | Medium candidate; loading, spawning and farm suitability deferred |
| Fortress + Bastion Overlap | Rename Close Fortress & Bastion: starts <=64 Nether blocks, both inside declared Nether scope | Medium integration/easy pair geometry; not physical overlap or farm suitability |
| Intersecting Triple Mineshaft | No preserved physical intersection/spawner promise; a renamed nearby-start trio is possible but weak | Defer advertised product |
| All-Biome 1,000m Sprint | Rename 14-Family Biome Sampler: >=14 explicitly enumerated OW families within1000 horizontal blocks at declared Y layers | Medium expanded OW registry and refinement; no walking route claim; not satisfied by counting Nether families |
| Mega Cherry Grove | Bounded largest predicted cherry patch on declared fixed-Y grid, with explicit adjacency, area and span metrics | Medium/high candidate-only dense computation; current sparse samples cannot prove contiguity or globally largest biome |
| Badlands Continental Spine | Bounded largest predicted badlands patch | Medium/high revised model patch; exposed terrain, gold and mineshaft scenery deferred |
| Endless Deep Dark Void | None that preserves an open connected cave trench | Defer; biome labels do not prove cave air/connectivity |

The two largest-patch products should be a later medium-cost increment, not part
of the first automated launch. Exact grid connectivity is only connectivity of
the stated grid/provider; never promote it to physical terrain contiguity.
Farm candidates belong in a clearly separate candidate category, not under a
working-farm claim. Keep Technical Redstone & Farms gated; optional renamed
candidates go in Structure Clusters, without any loading-distance advice.
Proposed Top100 unique worlds per record, with scarce lists
allowed to have fewer or zero results. Existing illustrative 18–24 village etc.
numbers are not minimum thresholds. The other 28 proposed record categories do
not exist as definitions and should not block this launch or be invented now.

## Common proposal

Prefer procedural predictions for discovery; retain scoped BDS evidence for
calibration/finalists. Unknown is not zero or proof of absence. Never discard a
world merely because a generated-world check was unavailable. Exhaustive complete
world verification at personal-screening throughput is not promised.

Preset/record publication uses finite surveyed scopes. Even a 2,000-radius circle
around spawn may extend beyond the current global observation envelope for an
outlier spawn: enrich required coverage or keep it pending, never clip silently.
Exact compatibility and per-type recall limitations remain visible, especially
stronghold references. The searched population consists of evaluated public
worlds, not every input passed through the cheap personal screen.
