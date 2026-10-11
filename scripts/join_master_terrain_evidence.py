"""Join retained model probes to actual saved block evidence without generation."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'runs/master-implementation-2026-10-10/terrain-attribution'


def main():
    source = ROOT / 'runs/realm-implementation-2026-10-10/final-bds-selected-check.json'
    saved = json.loads(source.read_text())
    observation = saved['observation']
    by_point = {(c['x'], c['z']): c for c in observation['evidence']['columns']}
    assert len(by_point) == len(observation['evidence']['columns'])
    with (OUT / 'columns.csv').open(newline='') as stream:
        models = list(csv.DictReader(stream))
    rows = []
    for model in models:
        point = (int(model['x']), int(model['z']))
        actual = by_point[point]
        assert float(model['observed_support_y']) == actual['ground']['y']
        exposed_water = actual['waterTop'] is not None
        assert (model['actual_exposed_water'] == 'True') == exposed_water
        rows.append({**model,
                     'actual_support_type': actual['ground']['block'],
                     'actual_top_y': actual['top']['y'],
                     'actual_top_type': actual['top']['block'],
                     'actual_ground_status': actual['groundStatus'],
                     'actual_exposed_water_top': actual['waterTop'],
                     'actual_exposed_water_bottom': actual['waterBottom'],
                     'actual_exposed_water_depth': actual['waterDepth'],
                     'actual_water_status': actual['waterStatus'],
                     'actual_primary_fluid_state': 'UNKNOWN_NOT_RECORDED',
                     'actual_overlay_fluid_state': 'UNKNOWN_NOT_RECORDED',
                     'actual_structure_cover_provenance': 'UNKNOWN_NOT_RECORDED',
                     'actual_discarded_cover': json.dumps(actual['discarded'], separators=(',', ':')),
                     'actual_block_probes': json.dumps(actual['probes'], separators=(',', ':')),
                     'actual_biome': actual.get('biome'),
                     'known_height_and_exposed_water': True,
                     'current_natural_ground_policy_verified': False})
    with (OUT / 'joined-columns.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    report = {'columns': len(rows), 'all_model_columns_joined': True,
              'source': str(source.relative_to(ROOT)),
              'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'model_columns_sha256': hashlib.sha256((OUT / 'columns.csv').read_bytes()).hexdigest(),
              'actual_identity': observation['identity'],
              'actual_raster_metadata': observation['raster']['metadata'],
              'current_natural_ground_policy_verified': False,
              'missing_channels': ['primary fluid state', 'overlay fluid state', 'structure-cover provenance'],
              'decision': 'Use retained support/top/cover/probe evidence for attribution. Exposed-water evidence does not establish waterlogging, ice, natural structure exclusion or complete formation coverage. Missing channels stay unknown; no accuracy or scoring promotion.'}
    (OUT / 'joined-evidence-report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('columns', 'all_model_columns_joined', 'missing_channels', 'decision')}, indent=2))


if __name__ == '__main__':
    main()
