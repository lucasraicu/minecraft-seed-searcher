# Discovery-size benchmark — 10 October 2026

The million pilot stopped after the structural/biome baseline. Its checkpoint contains **zero predictive terrain evaluations** and zero observations: the terrain pass count/rate is **unknown**, rather than a measured zero-pass result. Both V1/V2 task sets remain pending. Independent historical terrain/BDS controls are outside this cohort.

This quick comparison used the same first **5,000 full64 inputs** as the million pilot: **three alternating-order trials per size**, **30 processes × 1 native thread**, 45,000 evaluations in total. Both initial Overworld and Nether discovery squares changed. The final Stronghold-centered Overworld remained **2688 × 2688**, Nether remained exact **1024 × 1024**, and both Fortress and Bastion remained mandatory.

| Initial discovery square | Median seeds/s (range) | Unique baseline-qualifying seeds / 5,000 | Qualifying anchors | Qualifying anchors/s | Anchors retained versus 5000 |
|---|---:|---:|---:|---:|---:|
| 5000 × 5000 | 193.77 (192.12–198.34) | 3,351 | 6,052 | 234.54 | 100.00% |
| 4000 × 4000 | 267.90 (263.93–273.99) | 2,747 | 4,297 | 230.23 | 71.00% |
| 3000 × 3000 | 440.59 (428.68–441.07) | 1,896 | 2,498 | 220.12 | 41.28% |

The 4000 square is **38.25% faster**, retaining **71.00%** of qualifying anchors; qualifying anchors/s decreases **1.84%**. The 3000 square is **127.37% faster**, retaining **41.28%**; qualifying anchors/s decreases **6.15%**. Distinct qualifying seeds/s increases from **129.87** to **147.18** and **167.07**. Those seeds offer fewer alternative Stronghold anchors, whose terrain suitability has not yet been evaluated.

For a speed/coverage compromise, 4000 costs fewer opportunities than 3000 while keeping almost the same qualifying-anchor rate. Retain 5000 when broader anchor coverage is the priority. No setting was promoted automatically.

Repeated memberships match; each smaller discovered/qualifying set is exactly the 5000 set restricted to that smaller half-open discovery square. Native/config identities match the completed million launch, and all 191 previously sealed source hashes remain unchanged. These bounded controls protect predictor reproducibility; they do not prove actual-game discovery recall.

These are fresh-small-database **baseline-only** rates, including worker startup/IPC/checkpointing. Terrain and BDS are excluded. Do not treat them as sustained million-run rates or verified-world throughput. Production configuration is unchanged.

Evidence: [report.json](report.json), [million terrain status](million-terrain-status.json), [production identity](production-identity.json), [verification](verification.json). Reproduce with the separate [diagnostic script](../../scripts/measure_master_discovery.py) and a fresh output directory.
