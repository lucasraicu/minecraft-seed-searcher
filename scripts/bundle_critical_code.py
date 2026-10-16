"""Bundle all crucial active production code files into AUDIT_CRITICAL_CODE.md for Claude."""
from pathlib import Path

FILES = [
    # C11 Kernel & Native Engine
    ("native/blueprint_batch.h", "c", "C11 Header Struct Definitions (NBPolicy, NBCandidate, NBDynamicCell, NBWorker)"),
    ("native/blueprint_dynamic.inc", "c", "C11 Dynamic Envelope 2048-v3 Kernel (Stage 1A/1B, Sliding Window, Biome Prefix, Cutoff Pruning)"),
    ("native/blueprint_batch.inc", "c", "C11 OpenMP Multi-Threaded Batch Sweep, Buffer Retention & Memory Manager"),
    ("vendor/cubiomes-bedrock/rng.h", "c", "Cubiomes PRNG & Branchless floordiv(a, b) Definition"),

    # Python Scoring Oracle, Specification & Runtime
    ("src/seed_search/realm/config.py", "python", "Specification Source of Truth: dynamic_v3_blueprint_config(), 14 Hard Floors & Bounds"),
    ("src/seed_search/realm/blueprint.py", "python", "Python Reference Scoring Oracle: dynamic_v3_score() 1,250 Pts Model & evaluate_dynamic_seed()"),
    ("src/seed_search/realm/dynamic.py", "python", "Python Spatial Geometry: 256-point Nether Lattice, Centroid Snapping, Scenic, Spread, Bastion"),
    ("src/seed_search/realm/top_tracker.py", "python", "Top-50 In-Memory Priority Queue, RevStr Lexical Inversion, Tie-Breaking"),
    ("src/seed_search/realm/reports.py", "python", "Candidate Rescore Idempotence, Dispatch & Serialization (_candidate_rescore)"),
    ("src/seed_search/realm/native_batch.py", "python", "Python CFFI Engine Wrapper: Prototype, Buffer Decoding & persist_pipeline()"),

    # Sweeps & Testing
    ("scripts/pilot_v3_2048.py", "python", "Production Sweep Runner with Dynamic Top-50 Cutoff Feedback Loop"),
    ("tests/test_dynamic_v3_2048.py", "python", "Core Dynamic-Envelope-2048-v3 Verification Suite (17 Tests)"),

    # Web UI Contracts
    ("web-ui/src/constants/searchProfiles.json", "json", "Web UI Profile Registry: dynamic2048 Profile, Floors & Miss Budget"),
    ("web-ui/src/utils/ranking.ts", "typescript", "Web UI Sorting Comparator: Score-First Ordering (compareCandidateRank)"),
    ("tests/web_structure_policy.cjs", "javascript", "Web UI & Backend Policy Contract Test Suite (13 Tests)")
]

out = [
    "# Minecraft Seed Searcher (`dynamic-envelope-2048-v3`) — Master Critical Codebase Bundle\n",
    "> **Notice for Claude:**\n",
    "> This file contains the complete, uncompressed, verbatim source code for all 15 crucial files comprising the `dynamic-envelope-2048-v3` architecture as of commit `9e3f3a7`.\n",
    "> Below is the executive response to your preliminary findings, followed by the complete source code for each file.\n\n",
    "## Executive Clarifications to Claude's Preliminary Findings\n\n",
    "1. **Macro Region Union vs. Origin Windows (Finding 1):**\n",
    "   The macro stage does NOT test an origin-centered `[-1024, 1024]` window. In `native/blueprint_dynamic.inc:880`, `feasible` is initialized to `{-2000, -2000, 1999, 1999}` (the full discovery bounds). In `nb_dynamic_raw_bounds_core` (lines 713–758), `xmin` and `xmax` are computed across all valid raw Nether co-window pairs and set `feasible = [xmin - ow_half, zmin - ow_half, xmax + ow_half - 1, zmax + ow_half - 1]`. It is strictly the union of all feasible windows (spanning up to `[-2000, 2000]`), so seeds with clusters in offset windows are never falsely pruned.\n\n",
    "2. **C vs. Python Integer Division Rounding (Finding 2):**\n",
    "   The C code does NOT use plain `/` or `%` for coordinate math. It calls `floordiv(a, b)` defined in `vendor/cubiomes-bedrock/rng.h:75`:\n",
    "   ```c\n",
    "   static inline int32_t floordiv(int32_t a, int32_t b) {\n",
    "       int32_t q = a / b;\n",
    "       int32_t r = a % b;\n",
    "       return q - ((a ^ b) < 0 && !!r);\n",
    "   }\n",
    "   ```\n",
    "   This is branchless flooring division identical to Python's `//` (e.g. `floordiv(-7, 8) == -1`, `floordiv(-9, 8) == -2`). All coordinate downscaling (`C/8`, chunk 16, lattice 64) uses `floordiv`.\n\n",
    "3. **Wave 3 Speedup Attribution (Finding 4):**\n",
    "   You are 100% correct. Under $B=0$ with 0 survivors, the Top-50 tracker remains empty (`cutoff_score = 0`), so the early-abort gates could not have fired during natural sweeps. The 59.2k -> 63.1k jump was run-to-run CPU burst variance and cache warmness, not cutoff pruning.\n\n",
    "4. **C Memory Safety & Cell Cap (Q3):**\n",
    "   In `blueprint_dynamic.inc:1010-1019`, `dyn_ex` and `dyn_ez` grow via temp pointers (`new_ex`, `new_ez`) and check `if (!new_ex || !new_ez) { free(...); code = -3; goto done; }`. For sliding cells, line 1046 enforces a hard cap: `if (maxcells > 10000000) { code = -3; goto done; }` which aborts safely without crashing.\n\n",
    "5. **Luxury Biome Arithmetic (Finding 5):**\n",
    "   The luxury bonus list in Python has 10 luxury scoring buckets totaling 240 pts + threshold bonuses (>=5 gives +10, >=7 gives +25) for 265 pts total. The Outpost floor is 1 with surplus ladder `{0, 15, 30, 40}`.\n\n",
    "---\n\n",
    "## Table of Contents & Manifest\n\n",
    "| # | File Path | Language | Lines | Description |\n",
    "| :--- | :--- | :--- | :--- | :--- |\n"
]

total_lines = 0
file_records = []
for rel_path, lang, desc in FILES:
    p = Path(rel_path)
    if not p.is_file():
        raise FileNotFoundError(f"Missing file: {rel_path}")
    text = p.read_text()
    lines = len(text.splitlines())
    total_lines += lines
    file_records.append((rel_path, lang, desc, text, lines))

for idx, (rel_path, lang, desc, text, lines) in enumerate(file_records, 1):
    out.append(f"| {idx} | [`{rel_path}`](#file-{idx}) | {lang.upper()} | {lines:,} | {desc} |\n")

out.append(f"\n**Total Lines of Crucial Code:** {total_lines:,}\n\n---\n\n")

for idx, (rel_path, lang, desc, text, lines) in enumerate(file_records, 1):
    fence = "```"
    out.append(f"<a id=\"file-{idx}\"></a>\n")
    out.append(f"### File {idx}: `{rel_path}`\n")
    out.append(f"> **Purpose:** {desc}  \n")
    out.append(f"> **Length:** {lines:,} lines | **Language:** {lang.upper()}\n\n")
    out.append(f"{fence}{lang}\n{text}\n{fence}\n\n---\n\n")

target = Path("AUDIT_CRITICAL_CODE.md")
target.write_text("".join(out))
print(f"Successfully created {target}: {target.stat().st_size:,} bytes across {total_lines:,} lines in {len(FILES)} files.")
