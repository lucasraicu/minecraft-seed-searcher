"""Read-only reuse of the historical million benchmark's retained positive evidence.

No world generation or new seed search. Counts are lower bounds where old stages
were skipped, and first biome witnesses give conservative presence in a crop.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import sqlite3
import time

NAMES = ('village', 'trial_chamber', 'ancient_city', 'mineshaft',
         'fortress', 'bastion', 'monument', 'outpost', 'shipwreck', 'ruined_portal')
PROFILES = {
    'core_one_each': {'village': 1, 'trial_chamber': 1, 'ancient_city': 1, 'mineshaft': 1},
    'two_core': {'village': 2, 'trial_chamber': 2, 'ancient_city': 2, 'mineshaft': 3},
    'more_core': {'village': 3, 'trial_chamber': 3, 'ancient_city': 2, 'mineshaft': 5},
    'more_core_three_cities': {'village': 3, 'trial_chamber': 3, 'ancient_city': 3, 'mineshaft': 5},
    'four_each_core': {'village': 4, 'trial_chamber': 4, 'ancient_city': 4, 'mineshaft': 4},
    'eight_each_core': {'village': 8, 'trial_chamber': 8, 'ancient_city': 8, 'mineshaft': 8},
    'previous_individual_core_maxima': {'village': 9, 'trial_chamber': 11, 'ancient_city': 7, 'mineshaft': 55},
}
BIO_PROFILES = {'forest2_taiga1': {'forest': 2, 'taiga': 1},
                'forest3_taiga2': {'forest': 3, 'taiga': 2}}


def inside(point, bounds):
    return bounds[0] <= point[0] < bounds[2] and bounds[1] <= point[1] < bounds[3]


def distinct_count(points, bounds):
    return len({tuple(p) for p in (points or ()) if inside(p, bounds)})


def paths():
    result = ['$.stronghold', '$.bounds.overworld', '$.bounds.final_nether']
    for name in NAMES:
        section = ('required_nether_structures' if name in ('fortress', 'bastion')
                   else 'required_structures' if name in ('village', 'trial_chamber', 'ancient_city', 'mineshaft')
                   else 'optional_structures')
        result.append(f'$.{section}.{name}.predicted_viable')
    result.append('$.biomes.raw_detections')
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='runs/master-implementation-2026-10-10')
    parser.add_argument('--output', default='runs/count-bits-2026-10-11/million-count-feasibility.json')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    dbpath = root / 'million/workers-30/realm.sqlite'
    launch = json.loads((root / 'benchmark-launch.json').read_text())
    benchmark = json.loads((root / 'million/benchmark.json').read_text())
    id_family = {}
    with Path('runs/count-bits-2026-10-11/biome-ids.csv').open() as f:
        for row in csv.DictReader(f):
            if row['dimension'] == '0': id_family[row['id']] = row['family']
    stats = {key: {'requirement': need, 'anchors': Counter(),
                   'seeds': {}, 'examples': {}} for key, need in PROFILES.items()}
    maxima = {n: {'count': 0} for n in NAMES}
    family_maxima = {n: {'count': 0} for n in set(id_family.values())}
    histograms = {n: Counter() for n in NAMES}
    kept_seeds = set()
    qualifications = Counter()
    total = kept = biome_rows = 0
    start = time.perf_counter()
    db = sqlite3.connect(dbpath.as_uri() + '?mode=ro', uri=True)
    try:
        assert json.loads(db.execute("SELECT value FROM meta WHERE key='completed_seeds'").fetchone()[0]) == 1_000_000
        sql = 'SELECT idx,seed,qualification,json_extract(result,' + ','.join("'"+p+"'" for p in paths()) + ') FROM candidates'
        for idx, seed, qualification, text in db.execute(sql):
            data = json.loads(text)
            center, original_ow, original_ne = data[:3]
            total += 1
            qualifications[qualification] += 1
            assert original_ow == [center[0]-1344, center[1]-1344, center[0]+1344, center[1]+1344]
            assert original_ne == [center[0]/8-512, center[1]/8-512, center[0]/8+512, center[1]/8+512]
            if not inside(center, (-2000, -2000, 2000, 2000)):
                continue
            kept += 1
            kept_seeds.add(seed)
            ow = (center[0]-768, center[1]-768, center[0]+768, center[1]+768)
            ne = (center[0]/8-448, center[1]/8-448, center[0]/8+448, center[1]/8+448)
            inventories = dict(zip(NAMES, data[3:3+len(NAMES)]))
            counts = {n: distinct_count(inventories[n], ne if n in ('fortress', 'bastion') else ow) for n in NAMES}
            evidence = {'index': int(idx), 'seed': seed, 'stronghold': center, 'counts': counts}
            for n, count in counts.items():
                histograms[n][count] += 1
                if count > maxima[n]['count']:
                    maxima[n] = {'count': count, 'example': evidence}
            families = Counter()
            detections = data[-1]
            if detections is not None:
                biome_rows += 1
                for bid, detection in detections.items():
                    p = detection['coordinate']
                    family = id_family.get(bid)
                    if family and inside((p[0],p[2]), ow): families[family] += 1
                for family, count in families.items():
                    if count > family_maxima[family]['count']:
                        family_maxima[family] = {'count': count, 'example': {'index': int(idx), 'seed': seed, 'stronghold': center}}
            for key, need in PROFILES.items():
                if not all(counts[n] >= required for n, required in need.items()): continue
                match_keys = ['overworld']
                if counts['fortress'] >= 1 and counts['bastion'] >= 1:
                    match_keys.append('overworld_and_nether')
                    for bkey, bneed in BIO_PROFILES.items():
                        if all(families[n] >= required for n, required in bneed.items()):
                            match_keys.append('overworld_nether_' + bkey + '_first_witness_lower_bound')
                st = stats[key]
                for mkey in match_keys:
                    st['anchors'][mkey] += 1
                    st['seeds'].setdefault(mkey, set()).add(seed)
                    if mkey not in st['examples']:
                        st['examples'][mkey] = {**evidence, 'first_witness_biome_family_counts': dict(families)}
            if total % 100_000 == 0:
                print(json.dumps({'candidates_scanned': total, 'retained_in_current_discovery': kept,
                                  'elapsed_seconds': round(time.perf_counter()-start, 1)}), flush=True)
        assert total == 2_629_026
        assert dict(qualifications) == {'PENDING': 1_426_716, 'PREDICTED': 1_202_310}
    finally:
        db.close()
    for st in stats.values():
        st['anchors'] = dict(st['anchors'])
        st['distinct_seeds'] = {key:len(v) for key,v in st.pop('seeds').items()}
    report = {
        'source_database': str(dbpath), 'source_database_bytes': dbpath.stat().st_size,
        'benchmark_report_sha256': hashlib.sha256((root/'million/benchmark.json').read_bytes()).hexdigest(),
        'historical_geometry': {'discovery_side': 5000, 'overworld_side': 2688, 'nether_side': 1024},
        'cropped_geometry': {'discovery_side': 4000, 'overworld_side': 1536, 'nether_side': 896},
        'input_seeds': benchmark['distinct_full64_inputs'], 'candidates_scanned': total,
        'original_qualification_counts': dict(qualifications),
        'retained_anchors_in_current_discovery': kept, 'distinct_seeds_with_retained_anchors':len(kept_seeds),
        'retained_anchors_with_old_biome_summary': biome_rows,
        'profile_results': stats, 'retained_positive_maxima':maxima,
        'first_biome_witness_family_maxima_lower_bounds':family_maxima,
        'retained_count_histograms':{n:dict(sorted(h.items())) for n,h in histograms.items()},
        'histogram_zero_meaning':'No retained positive start in the crop; this includes unqueried observations and is not confirmed absence.',
        'elapsed_seconds': time.perf_counter()-start,
        'limitations': [
            'Positive evidence replay only; skipped checks and unvalidated negative predictions do not establish absence or complete current-border rejection rates.',
            'All retained Stronghold anchors inside current discovery are considered, not the separate pilot first-anchor policy.',
            'One stored Stronghold is the chosen anchor, not a complete count of Strongholds in the cropped border.',
            'Individual maxima are largest retained positive counts, not attainable mathematical ceilings or simultaneous maxima.',
            'Only ten structure categories have useful retained inventories; buried treasure and monster room were unsupported and other structure categories were unqueried.',
            'Old biome summaries store only first witnesses at Y=63; witnesses inside the new border establish positive sampled ID presence, witnesses outside do not establish absence inside.',
            'Biome family counts use distinct numeric active IDs, not sample-point counts; new four-Y world-aligned sampling is not reconstructed.',
            'No terrain evaluation or actual-game verification was performed by this reanalysis.',
            'This does not benchmark current generation throughput or lower32/lower48 acceleration.'
        ],
        'historical_backend':launch['identity']['backend']
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'output':str(output),'elapsed_seconds':report['elapsed_seconds'],
                      'profiles':{k:{'anchors':v['anchors'],'distinct_seeds':v['distinct_seeds']} for k,v in stats.items()},
                      'maxima':{k:v['count'] for k,v in maxima.items()}},indent=2),flush=True)

if __name__ == '__main__': main()
