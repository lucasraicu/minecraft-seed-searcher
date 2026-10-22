#!/usr/bin/env python3
"""Predictive finalist heuristics with explicit unimplemented BDS verification.

No generated blocks are inspected by this script. Docker availability is only a
readiness diagnostic and never upgrades a prediction to observed certification.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from seed_search.backend import Backend, model_metadata
from seed_search.realm.structure_accuracy import evaluate_finalist_accuracy


def is_docker_available() -> bool:
    docker_bin = shutil.which('docker')
    if not docker_bin:
        for candidate in ['/Applications/Docker.app/Contents/Resources/bin/docker', '/usr/local/bin/docker']:
            if Path(candidate).exists():
                docker_bin = candidate
                break
    if not docker_bin:
        return False
    try:
        res = subprocess.run([docker_bin, 'info'], capture_output=True, timeout=5)
        return res.returncode == 0
    except Exception:
        return False


def verify_finalist(seed: int, cx: int, cz: int, skip_docker: bool = False, backend=None) -> dict:
    own_backend = False
    if backend is None:
        b = Backend(seed)
        own_backend = True
    else:
        b = backend
    try:
        # 1. Collect structures within half-open 2048 window: [cx - 1024, cx + 1024) x [cz - 1024, cz + 1024)
        x_min, x_max = cx - 1024, cx + 1024
        z_min, z_max = cz - 1024, cz + 1024
        bounds = (x_min, z_min, x_max, z_max)

        # Discovery scope: strongholds may be discovered in larger bounds
        discovery_bounds = (cx - 2048, cz - 2048, cx + 2048, cz + 2048)
        discovered_strongholds = b.structures('stronghold', discovery_bounds)

        # Clip strongholds to the same half-open 2048 window for counts and eligibility
        strongholds = [
            (x, z) for x, z in discovered_strongholds
            if x_min <= x < x_max and z_min <= z < z_max
        ]

        raw_villages = b.structures('village', bounds)
        villages = [(x, z) for x, z in raw_villages if x_min <= x < x_max and z_min <= z < z_max]

        raw_mansions = b.structures('mansion', bounds)
        mansions = [(x, z) for x, z in raw_mansions if x_min <= x < x_max and z_min <= z < z_max]

        raw_ancient_cities = b.structures('ancient_city', bounds)
        ancient_cities = [(x, z) for x, z in raw_ancient_cities if x_min <= x < x_max and z_min <= z < z_max]

        raw_trial_chambers = b.structures('trial_chamber', bounds)
        trial_chambers = [(x, z) for x, z in raw_trial_chambers if x_min <= x < x_max and z_min <= z < z_max]

        # 2. Tier A: Native predictive integrity check (clipped to window)
        tier_a = evaluate_finalist_accuracy(b, strongholds, villages)

        # 3. Tier B: BDS Ground Truth
        if skip_docker:
            tier_b = {
                'status': 'SKIPPED',
                'reason': 'Requested skip_docker configuration',
                'block_verification': 'NOT_RUN',
                'evidence_provenance': 'none'
            }
        elif not is_docker_available():
            tier_b = {
                'status': 'UNAVAILABLE',
                'reason': 'Docker daemon unavailable',
                'block_verification': 'NOT_RUN',
                'evidence_provenance': 'none'
            }
        else:
            # Docker info check only confirms daemon availability, not BDS image or chunk generation
            tier_b = {
                'status': 'PROVISION_ONLY',
                'reason': 'Docker daemon responsive; BDS container image provisioning and LevelDB block inspection not implemented',
                'block_verification': 'UNVERIFIED',
                'evidence_provenance': 'docker_daemon_check_only'
            }

        # Final verdict determination:
        # No BDS block verifier exists, so never claim actual certification.
        pred_pass = tier_a.get('prediction_pass')
        if pred_pass is True:
            final_verdict = 'PREDICTIVE_PASS'
        elif pred_pass is False:
            final_verdict = 'PREDICTIVE_FAILED'
        else:
            final_verdict = 'UNKNOWN'

        return {
            'seed': seed,
            'center': [cx, cz],
            'evaluation_window': [x_min, z_min, x_max, z_max],
            'discovery_scope': {
                'stronghold_discovery_bounds': list(discovery_bounds),
                'discovered_strongholds_count': len(discovered_strongholds),
                'window_clipped_strongholds_count': len(strongholds)
            },
            'counts_in_window': {
                'strongholds': len(strongholds),
                'villages': len(villages),
                'mansions': len(mansions),
                'ancient_cities': len(ancient_cities),
                'trial_chambers': len(trial_chambers)
            },
            'tier_a_predictive_accuracy': tier_a,
            'tier_b_bds_ground_truth': tier_b,
            'evidence_provenance': 'predictive_heuristics_tier_a_only',
            'evidence': {
                'source': 'pinned_native_predictor' if own_backend else 'injected_backend',
                'prediction_model': model_metadata()['model'] if own_backend else None,
                'dimension': 'overworld',
                'window_semantics': 'half_open_block_coordinates',
                'checked_predicates': ['predicted_portal_layout_and_depth', 'five_point_village_height_heuristic'],
                'observed_game_build': None,
                'generated_blocks_verified': False,
                'observation_artifact': None,
            },
            'final_verdict': final_verdict
        }
    finally:
        if own_backend:
            b.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=int, required=True, help='Candidate world seed')
    parser.add_argument('--center-x', type=int, default=0, help='Evaluation center X')
    parser.add_argument('--center-z', type=int, default=0, help='Evaluation center Z')
    parser.add_argument('--skip-docker', action='store_true', help='Skip Tier B Docker BDS execution')
    parser.add_argument('--output', type=Path, required=True, help='Output JSON report path')
    args = parser.parse_args()

    report = verify_finalist(args.seed, args.center_x, args.center_z, args.skip_docker)
    
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(f"Verification report written to: {args.output}")
    print(f"Verdict: {report['final_verdict']} (Accuracy Score: {report['tier_a_predictive_accuracy']['accuracy_score']})")


if __name__ == '__main__':
    main()

