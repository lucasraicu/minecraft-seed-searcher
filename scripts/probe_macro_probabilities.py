#!/usr/bin/env python3
"""Fast macro-envelope structure probability probe for dynamic-v3."""
from __future__ import annotations

import argparse
from collections import Counter
import sys
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from seed_search.backend import Backend
from seed_search.realm.config import dynamic_v3_blueprint_config
from seed_search.seeds import seed_from_index


def probe_macro(count: int = 5_000, run_key: int = 2026101501):
    cfg = dynamic_v3_blueprint_config()
    ow_macro = tuple(cfg["discovery"]["overworld_bounds"])
    nw_macro = tuple(cfg["discovery"]["nether_bounds"])

    floors = {
        "stronghold": 1,
        "mansion": 1,
        "monument": 1,
        "outpost": 1,
        "fortress": 1,
        "bastion": 2,
        "village": 6,
        "trial_chamber": 8,
        "ancient_city": 2,
        "desert_pyramid": 1,
        "jungle_temple": 1,
        "shipwreck": 4,
        "ruined_portal": 8,
        "mineshaft": 10,
    }

    pass_counts = Counter()
    joint_all = 0

    t0 = time.perf_counter()

    for i in range(count):
        seed = seed_from_index(i, run_key)
        with Backend(seed) as b:
            # Strongholds
            sh = b.structures("stronghold", ow_macro)
            has_sh = len(sh) >= floors["stronghold"]
            if has_sh:
                pass_counts["stronghold"] += 1

            # Mansion
            man = b.structures("mansion", ow_macro)
            has_man = len(man) >= floors["mansion"]
            if has_man:
                pass_counts["mansion"] += 1

            # Monument
            mon = b.structures("monument", ow_macro)
            has_mon = len(mon) >= floors["monument"]
            if has_mon:
                pass_counts["monument"] += 1

            # Outpost
            out = b.structures("outpost", ow_macro)
            has_out = len(out) >= floors["outpost"]
            if has_out:
                pass_counts["outpost"] += 1

            # Fortress
            fort = b.structures("fortress", nw_macro)
            has_fort = len(fort) >= floors["fortress"]
            if has_fort:
                pass_counts["fortress"] += 1

            # Bastion
            bast = b.structures("bastion", nw_macro)
            has_bast = len(bast) >= floors["bastion"]
            if has_bast:
                pass_counts["bastion"] += 1

            # Village
            vil = b.structures("village", ow_macro)
            has_vil = len(vil) >= floors["village"]
            if has_vil:
                pass_counts["village"] += 1

            # Trial Chamber
            tc = b.structures("trial_chamber", ow_macro)
            has_tc = len(tc) >= floors["trial_chamber"]
            if has_tc:
                pass_counts["trial_chamber"] += 1

            # Ancient City
            ac = b.structures("ancient_city", ow_macro)
            has_ac = len(ac) >= floors["ancient_city"]
            if has_ac:
                pass_counts["ancient_city"] += 1

            # Desert Pyramid
            dp = b.structures("desert_pyramid", ow_macro)
            has_dp = len(dp) >= floors["desert_pyramid"]
            if has_dp:
                pass_counts["desert_pyramid"] += 1

            # Jungle Temple
            jt = b.structures("jungle_temple", ow_macro)
            has_jt = len(jt) >= floors["jungle_temple"]
            if has_jt:
                pass_counts["jungle_temple"] += 1

            # Shipwreck
            sw = b.structures("shipwreck", ow_macro)
            has_sw = len(sw) >= floors["shipwreck"]
            if has_sw:
                pass_counts["shipwreck"] += 1

            # Ruined Portal
            rp = b.structures("ruined_portal", ow_macro)
            has_rp = len(rp) >= floors["ruined_portal"]
            if has_rp:
                pass_counts["ruined_portal"] += 1

            # Mineshaft
            ms = b.structures("mineshaft", ow_macro)
            has_ms = len(ms) >= floors["mineshaft"]
            if has_ms:
                pass_counts["mineshaft"] += 1

            if (
                has_sh
                and has_man
                and has_mon
                and has_out
                and has_fort
                and has_bast
                and has_vil
                and has_tc
                and has_ac
                and has_dp
                and has_jt
                and has_sw
                and has_rp
                and has_ms
            ):
                joint_all += 1

    t1 = time.perf_counter()

    print("=" * 78)
    print(f"MACRO-ENVELOPE STRUCTURE PROBABILITY PROBE ({count:,} SEEDS)")
    print(f"Elapsed: {t1 - t0:.2f}s ({(count / (t1 - t0)):,.1f} seeds/sec)")
    print("=" * 78)
    for name, floor in floors.items():
        cnt = pass_counts[name]
        pct = (cnt / count) * 100
        print(f"  {name:<16}: floor={floor:2d} | pass: {cnt:5d}/{count:5d} ({pct:6.2f}%)")

    print("-" * 78)
    print(f"Seeds with ALL 14 floors present in the MACRO-envelope: {joint_all}/{count} ({joint_all/count*100:.4f}%)")
    print("=" * 78)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=5_000, help="Number of seeds to probe (default: 5,000)")
    parser.add_argument("--run-key", type=int, default=2026101501, help="Seed run key")
    args = parser.parse_args()

    probe_macro(count=args.count, run_key=args.run_key)


if __name__ == "__main__":
    main()
