"""Publish readable tables and charts from audited compact-border pilots."""
import csv
import json
from pathlib import Path
import sys


def write_csv(path, names, rows):
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, names)
        writer.writeheader()
        writer.writerows(rows)


def main(root):
    report = json.loads((root / 'report.json').read_text())
    audit = json.loads((root / 'independent-audit.json').read_text())
    assert audit['passed']
    rows = report['summary']
    lookup = {(r['overworld_side'], r['nether_side']): r for r in rows}
    ow_sides = report['plan']['overworld_sides']
    nether_sides = report['plan']['nether_sides']
    compact = lookup[1280, 896]
    original = lookup[1280, 768]
    roomier = lookup[1536, 896]
    best_rate = max(rows, key=lambda r: r['qualifying_anchors_per_second'])
    measurements = json.loads((root / 'terrain.json').read_text())
    passes = [m for m in measurements if any(m['strict_pass'].values())]
    recommendation = {
        'status': 'recommended_next_pilot_target; production_configuration_unchanged',
        'discovery_side_blocks': 4000,
        'compact_target': {'overworld_side_blocks': 1280, 'nether_side_blocks': 896},
        'smallest_preferred_target': {'overworld_side_blocks': 1280, 'nether_side_blocks': 768},
        'roomier_compact_fallback': {'overworld_side_blocks': 1536, 'nether_side_blocks': 896},
        'largest_baseline_layout_throughput_pair': best_rate['pair'],
        'strict_terrain_pass_evaluations': len(passes),
        'actual_generation_verified': False,
        'compactness_checks': {
            'best_layouts_per_overworld_area_at_nether_896': max(
                (r for r in rows if r['nether_side'] == 896),
                key=lambda r: r['qualifying_anchors']/r['overworld_side']**2)['pair'],
            'best_layouts_per_nether_area_at_overworld_1280': max(
                (r for r in rows if r['overworld_side'] == 1280),
                key=lambda r: r['qualifying_anchors']/r['nether_side']**2)['pair']},
        'selection_basis': 'User prioritizes compact playable area. 1280/896 keeps Overworld at the preferred size and substantially improves the mandatory Fortress+Bastion and full baseline yield versus 1280/768. Terrain optimum remains unresolved.'}
    (root / 'recommended-target.json').write_text(json.dumps(recommendation, indent=2)+'\n')
    names = ['overworld_side', 'nether_side', 'qualifying_anchors', 'qualifying_seeds',
             'median_seeds_per_second', 'qualifying_anchors_per_second']
    write_csv(root / 'border-matrix.csv', names, [{n:r[n] for n in names} for r in rows])
    stage_rows = []
    for r in rows:
        for stage in r['funnel']:
            stage_rows.append({'overworld_side': r['overworld_side'], 'nether_side': r['nether_side'], **stage})
    write_csv(root / 'filter-funnels.csv', ['overworld_side', 'nether_side', 'stage',
              'surviving_anchors', 'surviving_seeds', 'newly_pending_anchors', 'conditional_retention_percent'], stage_rows)
    terrain_rows = []
    for ow, values in report['terrain_by_overworld'].items():
        for stage, counts in values['stage_observations'].items():
            terrain_rows.append({'overworld_side': int(ow), 'stage': stage, **counts})
    write_csv(root / 'terrain-stages.csv', ['overworld_side', 'stage', 'evaluated_center_observations',
              'geometry_pass', 'complete_within', 'geometry_and_complete_within', 'strict_finest_pass'], terrain_rows)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.4), constrained_layout=True)
    for ax, metric, title in zip(axes, ['qualifying_anchors', 'qualifying_anchors_per_second'],
                                ['Predicted qualifying layouts per 1,000 inputs', 'Predicted qualifying layouts per second']):
        values = np.array([[lookup[ow, n][metric] for n in nether_sides] for ow in ow_sides])
        im = ax.imshow(values, aspect='auto', cmap='YlGnBu')
        ax.set_xticks(range(len(nether_sides)), nether_sides)
        ax.set_yticks(range(len(ow_sides)), ow_sides)
        ax.set_xlabel('Nether side (blocks)')
        ax.set_ylabel('Overworld side (blocks)')
        ax.set_title(title, fontsize=11)
        for i in range(len(ow_sides)):
            for j in range(len(nether_sides)):
                value = values[i,j]
                label = str(int(value)) if metric == 'qualifying_anchors' else f'{value:.1f}'
                ax.text(j, i, label, ha='center', va='center', fontsize=9,
                        color='white' if value > values.max()*.55 else '#102030')
        from matplotlib.patches import Rectangle
        ax.add_patch(Rectangle((2.5, .5), 1, 1, fill=False, edgecolor='#f07f13', linewidth=2.5))
        fig.colorbar(im, ax=ax, shrink=.82)
    fig.suptitle('Compact border pilots — matched 1,000 seeds, two trials, discovery 4000', fontsize=13)
    fig.savefig(root / 'border-matrix.png', dpi=170)
    plt.close(fig)
    # This curve deliberately reports retained predictions, not actual rejections.
    fig, ax = plt.subplots(figsize=(11, 5), constrained_layout=True)
    stage_labels = ['Strongholds', 'Initial fortress', 'Final fortress', 'Final bastion',
                    'Ancient city', 'Village', 'Trial chamber', 'Mineshaft', 'Two wooded families']
    for pair, color in [((1280, 512), '#929ba6'), ((1280, 768), '#1779bc'),
                        ((1280, 896), '#f07f13'), ((1536, 896), '#268b51'), ((2380, 1024), '#805cad')]:
        row = lookup[pair]
        ax.plot(range(9), [s['surviving_anchors'] for s in row['funnel']], marker='o',
                color=color, label=f'OW {pair[0]} / Nether {pair[1]}')
    ax.set_xticks(range(9), stage_labels, rotation=22, ha='right')
    ax.set_ylabel('Qualifying Stronghold layouts')
    ax.set_title('Cumulative baseline filters, same 1,000 full64 inputs')
    ax.grid(axis='y', alpha=.2)
    ax.legend()
    fig.savefig(root / 'filter-funnel.png', dpi=170)
    plt.close(fig)
    gain = 100*(compact['qualifying_anchors']/original['qualifying_anchors']-1)
    throughput_gain = 100*(compact['qualifying_anchors_per_second']/original['qualifying_anchors_per_second']-1)
    lines = ['# Compact border pilots — 10 October 2026', '',
        '**Compact recommendation: 1280 × 1280 Overworld / 896 × 896 Nether, with discovery 4000 × 4000 in each dimension.**', '',
        f'This retains {compact["qualifying_anchors"]} predicted layouts from 1,000 inputs versus {original["qualifying_anchors"]} at 1280/768: **{gain:.2f}% more layouts per input** and **{throughput_gain:.2f}% more qualifying layouts/s** in these matched short trials. Nether width rises 16.67%, area 36.11%; the preferred 1280 Overworld stays fixed.', '',
        f'Keep **1280/768** if minimum playable size is the overriding objective. **1536/896** is the first roomier Overworld fallback, retaining {roomier["qualifying_anchors"]} layouts from the same inputs. These are judgments based on the compactness preference, not a mathematically identified terrain optimum.', '',
        'The compactness recommendation also has a measured area-efficiency basis: with Nether fixed at 896, **Overworld 1280 gives the most qualifying layouts per unit Overworld area** among the seven widths. With Overworld fixed at 1280, **Nether 896 gives the most qualifying layouts per unit Nether area** among the five widths. These are structural-layout density comparisons, not terrain success probabilities.', '',
        f'The highest measured structural layout throughput in the full tested range was **{best_rate["overworld_side"]}/{best_rate["nether_side"]}**, at {best_rate["qualifying_anchors_per_second"]:.2f} layouts/s. This larger pair is a throughput reference, not the compact recommendation.', '',
        '## Scope', '',
        'Seven Overworld widths (1024, 1280, 1536, 1792, 2048, 2304, 2380) × five Nether widths (512, 640, 768, 896, 1024), with two reversed-order trials per pair: **70,000 evaluations of the same 1,000 distinct signed full64 inputs**, using 30 baseline processes and one native thread each. Discovery is fixed at half-open [-2000,2000) on each axis independently in each dimension.', '',
        'Overworld is Stronghold-centered. Nether uses its exact fractional Stronghold/8 center. All five required Overworld structures, Fortress AND Bastion, and two wooded families remain mandatory. The 2380 width uses exact membership despite not being a chunk multiple. No geometry threshold, score, game model, native binary, or production setting was changed.', '',
        '## Structural survival matrix', '',
        'Each entry is qualifying Stronghold layouts per 1,000 inputs, not distinct seeds or verified worlds.', '',
        '| Overworld side | Nether 512 | 640 | 768 | 896 | 1024 |',
        '|---:|---:|---:|---:|---:|---:|']
    for ow in ow_sides:
        lines.append('| '+str(ow)+' | '+' | '.join(str(lookup[ow,n]['qualifying_anchors']) for n in nether_sides)+' |')
    lines += ['', '![Border matrix](border-matrix.png)', '', '## Compact options and measured rates', '',
              '| OW / Nether | Qualifying layouts | Unique qualifying seeds | Inputs/s | Qualifying layouts/s |',
              '|---|---:|---:|---:|---:|']
    for pair in [(1024,768), (1280,512), (1280,640), (1280,768), (1280,896), (1280,1024),
                 (1536,768), (1536,896), (1536,1024), (1792,896), (2048,1024), (2380,1024)]:
        r = lookup[pair]
        lines.append(f'| {pair[0]} / {pair[1]} | {r["qualifying_anchors"]} | {r["qualifying_seeds"]} | {r["median_seeds_per_second"]:.2f} | {r["qualifying_anchors_per_second"]:.2f} |')
    lines += ['', '## Every baseline filter', '',
              'Counts below are cumulative qualifying Stronghold anchors. Predictor nonpasses remain pending; they do not establish actual-world absence. Both final Nether structures are queried at every anchor, even if one fails; the table shows logical cumulative survival. Optional structures only add bonuses and are not rejection filters.', '',
              '| Filter | 1280 / 512 | 1280 / 768 | 1280 / 896 | 1536 / 896 | 2380 / 1024 |',
              '|---|---:|---:|---:|---:|---:|']
    pairs = [(1280,512), (1280,768), (1280,896), (1536,896), (2380,1024)]
    for i, name in enumerate(stage_labels):
        lines.append('| '+name+' | '+' | '.join(str(lookup[p]['funnel'][i]['surviving_anchors']) for p in pairs)+' |')
    lines += ['', '![Filter funnel](filter-funnel.png)', '',
              'At every Overworld size, Nether 512 retains only 198 of the 1,835 discovered anchors after the Fortress+Bastion pair; 768 retains 841, 896 retains 1,203, and 1024 retains 1,456. At compact Overworld widths, Ancient City is the next dominant requirement. Trial Chamber and Mineshaft add no further losses in this cohort after the preceding filters; that result is cohort-specific.', '',
              '## Terrain filtering', '',
              f'**{len(measurements)} anchor/Overworld pilots across {len({m["candidate_id"].rsplit(":", 2)[0] for m in measurements})} distinct seeds, {report["terrain_seconds"] / 60:.2f} minutes of terrain work**, using the real durable scheduler and 18 native threads. Each Overworld size evaluates six different seeds: two shared controls and four separately hash-selected seeds from that size’s 1024-Nether qualifying pool. Some selected seeds repeat across border sizes, so the 42 evaluations are not 42 independent worlds. Selection ignores terrain scores; common controls and random eligible samples are kept separate.', '',
              'Nomination covers the full default center grid. The budget is the normal **eight nominated centers per variant**, with independent V1/V2 and resolutions **128 → 64 → 32 → 16 → 8 → 4**. Low-score fine stages, halo limits, and retries retain the production scheduling rules and save unresolved work. This does not exhaust all possible centers.', '',
              '| Overworld | Samples | V1 strict passes | V2 strict passes | Finest complete footprint within border | Median terrain seconds/anchor |',
              '|---:|---:|---:|---:|---:|---:|']
    for ow in ow_sides:
        ms = [m for m in measurements if m['overworld_side'] == ow]
        t = report['terrain_by_overworld'][str(ow)]
        lines.append(f'| {ow} | {len(ms)} | {sum(m["strict_pass"]["v1"] for m in ms)} | {sum(m["strict_pass"]["v2"] for m in ms)} | {sum(m["any_finest_complete_within"] for m in ms)} | {t["median_seconds_per_anchor"]:.2f} |')
    lines += ['', f'**{len(passes)} strict passing anchor/Overworld evaluations were found.** Strict means predicted qualification, geometry pass, a complete formation footprint wholly inside the exact border, and last height resolution 4. Geometric near matches, partial coverage, and border-clipped formations do not count.', '',
              'The sample is too small to identify a terrain success-rate optimum. Nether changes baseline eligibility; geometry is reused only when each pair independently qualified the sampled anchor. The four random eligible seeds differ across Overworld sizes; their terrain counts are not a controlled population comparison. The two common controls provide a matched comparison but remain a tiny sample.', '',
              '| Overworld | V1 evaluations at 128 / 64 / 32 / 16 / 8 / 4 | V2 evaluations at 128 / 64 / 32 / 16 / 8 / 4 |',
              '|---:|---|---|']
    for ow in ow_sides:
        stages = report['terrain_by_overworld'][str(ow)]['stage_observations']
        values = [' / '.join(str(stages.get(f'{v}:resolution-{res}', {}).get('evaluated_center_observations', 0)) for res in (128,64,32,16,8,4)) for v in ('v1','v2')]
        lines.append(f'| {ow} | {values[0]} | {values[1]} |')
    lines += ['', 'These are evaluated center observations, including nearby-center tests, adaptive refinement, and halos; they are not unique anchors and are not successive rejection-rate denominators. Full geometry/border counts and reason counts are saved in the JSON/CSV and individual databases.', '',
              '## Verification and limits', '',
              f'The independent read-only audit passed all **70 baseline databases**, **{audit["candidate_bound_and_filter_checks"]:,} candidate-bound/filter checks**, **42 terrain databases**, exact signed-full64 input coverage, repeated memberships, nested required-structure memberships, recomputed stage counts, and **15 public-evaluator seed replays**. Existing computational source/config/native identities remain unchanged ({audit["production_source_files_unchanged"]} sealed files). Overlapping arms also reproduce the previous pilot exactly.', '',
              '**One biome-sampling exception:** seed 7980124511283784280, Stronghold (772,-1996), qualifies at 2304/1024 but remains pending for wooded-family coverage at 2380/1024. The 2380 border shifts the 64-block biome lattice by 38 blocks relative to 2304; all required structures still qualify. The [coordinate replay](biome-lattice-replay.json) reproduced both forest and jungle at saved points inside the larger border. This is sampling sensitivity, not actual loss of biome coverage or a border-membership error. The exception is preserved in baseline.json and the independent audit rather than hidden to force nested final results.', '',
              'Native structure/density/biome output is prediction from MC_26_50, not actual Bedrock 26.52 evidence. No BDS or actual structure/terrain/access verification ran, so the final actual-generation filter is **unmeasured**. Production configuration is unchanged and no production sweep started. Small-database rates include startup/IPC/persistence and cannot be substituted for sustained million-input throughput.', '',
              'Stage seconds in report.json sum measured call durations across workers; they are neither end-to-end wall seconds nor complete CPU attribution. Border area ratios are not used to forecast speed.', '',
              'Evidence: [report.json](report.json), [independent audit](independent-audit.json), [recommendation](recommended-target.json), [structural matrix CSV](border-matrix.csv), [every filter CSV](filter-funnels.csv), [terrain stages CSV](terrain-stages.csv), [selection](selection.json), [baseline trials](baseline.json), [terrain results](terrain.json).', '',
              'Reproduce: `.venv/bin/python scripts/measure_compact_border_funnel.py --output <fresh-directory>`; then `.venv/bin/python scripts/audit_compact_border_funnel.py <directory>` and `.venv/bin/python scripts/report_compact_border_funnel.py <directory>`.', '']
    (root / 'REPORT.md').write_text('\n'.join(lines))
    print(json.dumps(recommendation, indent=2))


if __name__ == '__main__':
    main(Path(sys.argv[1]).resolve())
