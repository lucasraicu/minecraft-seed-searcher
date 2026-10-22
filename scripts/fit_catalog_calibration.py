#!/usr/bin/env python3
"""Fit declared count schedules and report held-out metrics from saved facts."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from calibrate_catalog_sizes import BASELINE_TIERS
from seed_search.catalog.artifacts import ArtifactStore
from seed_search.catalog.calibration import fit
from seed_search.catalog.geometry import bounds_for, inside
from seed_search.catalog.ingestion import atomic_json, strict_json_loads, verify_no_symlinks
from seed_search.catalog.models import validate_observation_v2
from seed_search.catalog.realm_evaluation import RealmScene
from seed_search.catalog.registry import digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = verify_no_symlinks(args.input.absolute())
    progress = strict_json_loads((root / 'progress.json').read_bytes())
    if progress.get('complete') is not True or not 1 <= len(progress['worlds']) <= 200:
        raise ValueError('Require a complete bounded calibration cohort')
    store = ArtifactStore(root / 'objects')
    rows = []
    for row in progress['worlds']:
        obs = validate_observation_v2(store.get_json(row['artifact']))
        if digest(obs) != row['observation_id']:
            raise ValueError('Calibration artifact differs')
        scene = RealmScene(obs, {})
        counts = {}
        for side in (2048, 4096, 8192):
            box = bounds_for([0, 0], side)
            values = {}
            for name in BASELINE_TIERS:
                source_name = 'igloo_basement' if name == 'igloo' else name
                if not scene.complete(source_name, box):
                    raise ValueError(f'Unknown calibration inventory: {row["seed"]}/{source_name}')
                values[name] = len(scene.captured(source_name, box))
            counts[str(side)] = values
        rows.append(dict(world_id=row['world_id'], split=row['split'], counts=counts))
    thresholds = fit(rows, {name: dict(floor=levels[0], levels=levels) for name, levels in BASELINE_TIERS.items()})
    artifact = dict(revision='catalog-realm-calibration-v1', status='review_pending',
        cohort_id=progress['cohort_id'], source_identity=progress['identity'], native_realm_pin=progress['native_realm_pin'],
        evidence_id=digest(progress['worlds']), thresholds=thresholds,
        budgets=dict(total=1250, overworld=845, luxury_biomes=265, nether=140),
        scoring=dict(luxury_side='selected_overworld', luxury_y=63, nether_side=1024,
                     local_geometry='unchanged_hub_scenic_net_proxy', candidate_policy='grid81-plus-coordinate-events-v1'),
        allocations={'2048':3334, '4096':3333, '8192':3333},
        split_policy='Frozen original cohort world-ID hash modulo5; never resplit after enrichment',
        limitations=['Existing200world catalog cohort; not a uniform sample of all seeds',
            'FixedOrigin calibration differs from optimized settlement selection',
            'Strongholds use bounded predictor enumeration, not a complete physical instance count',
            'Small unsampled biome patches may be missed; counts are viable predicted starts'])
    # Thresholds are frozen before reading held-out scores; no fit parameters are
    # selected from the metrics below.
    metrics = {}
    for row in progress['worlds']:
        obs = store.get_json(row['artifact'])
        scene = RealmScene(obs, artifact)
        for side in (2048, 4096, 8192):
            result = scene.evaluate([0,0], side, time.monotonic()+5)
            metrics.setdefault(row['split'], {}).setdefault(str(side), []).append(dict(
                world_id=row['world_id'], status=result['status'], score=result['score'],
                group_scores=result['group_scores'], missing=result['missing']))
    artifact['metrics'] = {split:{side:dict(n=len(group), qualifying=sum(r['status']=='match' for r in group),
        pending=sum(r['status']=='pending' for r in group), scores=dict(sorted(Counter(r['score'] for r in group).items())),
        groups={name:dict(sorted(Counter(r['group_scores'][name] for r in group).items())) for name in ('overworld','luxury_biomes','nether')})
        for side,group in sizes.items()} for split,sizes in metrics.items()}
    atomic_json(args.output, artifact)
    atomic_json(Path(str(args.output)+'.scores.json'), metrics)
    print(json.dumps(dict(output=str(args.output), calibration_id=digest(artifact), metrics=artifact['metrics'])), flush=True)


if __name__ == '__main__':
    main()
