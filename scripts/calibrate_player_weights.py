#!/usr/bin/env python3
"""Bradley-Terry discrete choice utility calibration solver for Bedrock survival realms.

Fits empirical player utility weights from blinded pairwise A/B comparison data:
- Features: [D_daily (m), D_milestone (m), A_build (ha), R_diversity (0-1)]
- Models: P(A > B) = 1 / (1 + exp(-beta^T (u_A - u_B)))
- Constrains parameters to respect monotonicity and survival priorities:
  * beta_daily < 0 (daily travel penalty)
  * beta_milestone < 0 (milestone travel penalty)
  * |beta_daily| >= 1.2 * |beta_milestone| (daily commute dominates milestone)
  * beta_build > 0 (reward for contiguous buildable land)
  * beta_diversity > 0 (reward for multiplayer resource saturation)
"""
import argparse
import json
import math
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))


def default_preference_pairs() -> List[Dict]:
    """Synthetic baseline calibration pairs grounded in Bedrock realm tradeoffs."""
    return [
        # Pair 1: Close village (120m) vs Distant village (750m) with equal stronghold
        {
            'seed_a': 'close_village',
            'seed_b': 'distant_village',
            'u_a': [180.0, 950.0, 1.2, 0.75],
            'u_b': [540.0, 950.0, 1.2, 0.75],
            'preferred': 'A',  # Close village wins easily
            'weight': 1.0,
            'dataset_type': 'synthetic_demonstration'
        },
        # Pair 2: Close village (200m) + distant stronghold (1100m) vs distant village (800m) + close stronghold (350m)
        {
            'seed_a': 'close_v_far_sh',
            'seed_b': 'far_v_close_sh',
            'u_a': [240.0, 1050.0, 1.5, 0.80],
            'u_b': [580.0, 620.0, 1.5, 0.80],
            'preferred': 'A',  # Realm builders prefer daily village access over once-per-season End trip
            'weight': 1.0,
            'dataset_type': 'synthetic_demonstration'
        },
        # Pair 3: Flat buildable land (3.5 ha) vs Mountainous crags (0.2 ha) with identical travel
        {
            'seed_a': 'flat_plains_hub',
            'seed_b': 'craggy_peaks_hub',
            'u_a': [320.0, 850.0, 3.5, 0.70],
            'u_b': [320.0, 850.0, 0.2, 0.70],
            'preferred': 'A',  # Community builders strongly prefer flat building land
            'weight': 1.0,
            'dataset_type': 'synthetic_demonstration'
        },
        # Pair 4: High resource saturation (10 chambers, 8 villages) vs low saturation (3 chambers, 2 villages)
        {
            'seed_a': 'high_saturation',
            'seed_b': 'starved_saturation',
            'u_a': [300.0, 900.0, 1.0, 0.95],
            'u_b': [300.0, 900.0, 1.0, 0.35],
            'preferred': 'A',  # Multiplayer realms require shared resources without starvation
            'weight': 1.0,
            'dataset_type': 'synthetic_demonstration'
        },
        # Pair 5: Mansion 400m away vs Extra village 300m away
        {
            'seed_a': 'close_second_village',
            'seed_b': 'close_mansion',
            'u_a': [210.0, 950.0, 1.0, 0.85],
            'u_b': [420.0, 650.0, 1.0, 0.75],
            'preferred': 'A',  # Village iron/trading beats one-time raid trophy
            'weight': 1.0,
            'dataset_type': 'synthetic_demonstration'
        }
    ]


def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -35.0, 35.0)))


def fit_bradley_terry(pairs: List[Dict], l2_reg: float = 0.01) -> Dict:
    if not isinstance(pairs, list) or len(pairs) == 0:
        raise ValueError("Input pairs must be a non-empty list of comparison dicts")

    if not isinstance(l2_reg, (int, float, np.number)) or not math.isfinite(float(l2_reg)) or float(l2_reg) < 0.0:
        raise ValueError(f"l2_reg must be a non-negative finite float, got {l2_reg}")

    X = []
    y = []
    sample_weights = []

    for i, p in enumerate(pairs):
        if not isinstance(p, dict):
            raise ValueError(f"Pair index {i} must be a dictionary")
        if 'u_a' not in p or 'u_b' not in p or 'preferred' not in p:
            raise ValueError(f"Pair index {i} missing required keys ('u_a', 'u_b', 'preferred')")

        u_a = p['u_a']
        u_b = p['u_b']
        if not hasattr(u_a, '__len__') or len(u_a) != 4:
            raise ValueError(f"Pair index {i}: u_a must have length 4, got {len(u_a) if hasattr(u_a, '__len__') else type(u_a)}")
        if not hasattr(u_b, '__len__') or len(u_b) != 4:
            raise ValueError(f"Pair index {i}: u_b must have length 4, got {len(u_b) if hasattr(u_b, '__len__') else type(u_b)}")

        for val in list(u_a) + list(u_b):
            if not isinstance(val, (int, float, np.number)) or not math.isfinite(float(val)):
                raise ValueError(f"Pair index {i}: Feature values must be finite numbers, got {val}")

        pref = p['preferred']
        if pref not in ('A', 'B'):
            raise ValueError(f"Pair index {i}: Invalid preferred value '{pref}', must be 'A' or 'B'")

        weight = p.get('weight', 1.0)
        if not isinstance(weight, (int, float, np.number)) or not math.isfinite(float(weight)) or float(weight) <= 0.0:
            raise ValueError(f"Pair index {i}: Sample weight must be a positive finite number, got {weight}")

        u_a_arr = np.array(u_a, dtype=np.float64)
        u_b_arr = np.array(u_b, dtype=np.float64)
        delta_u = u_a_arr - u_b_arr
        # Normalize scale: commute distances (divide by 500m), buildable (divide by 2 ha)
        scale = np.array([1.0 / 500.0, 1.0 / 500.0, 1.0 / 2.0, 1.0], dtype=np.float64)
        scaled_delta = delta_u * scale

        pref_a = 1.0 if pref == 'A' else 0.0
        X.append(scaled_delta)
        y.append(pref_a)
        sample_weights.append(float(weight))

    X = np.array(X, dtype=np.float64)
    y = np.array(y, dtype=np.float64)
    weights = np.array(sample_weights, dtype=np.float64)

    # Initial beta: [d_daily < 0, d_milestone < 0, buildable > 0, diversity > 0]
    beta_init = np.array([-1.5, -0.6, 1.0, 1.2])

    def loss(beta):
        logits = X @ beta
        probs = sigmoid(logits)
        # Binary cross-entropy with sample weights
        eps = 1e-12
        bce = -np.sum(weights * (y * np.log(probs + eps) + (1.0 - y) * np.log(1.0 - probs + eps)))
        reg = 0.5 * l2_reg * np.sum(beta ** 2)
        return bce + reg

    def grad(beta):
        logits = X @ beta
        probs = sigmoid(logits)
        error = weights * (probs - y)
        d_bce = X.T @ error
        d_reg = l2_reg * beta
        return d_bce + d_reg

    # Optimization bounds:
    # beta_daily in [-5.0, -0.2]
    # beta_milestone in [-3.0, -0.05]
    # beta_build in [0.2, 5.0]
    # beta_diversity in [0.2, 5.0]
    bounds = [(-5.0, -0.2), (-3.0, -0.05), (0.2, 5.0), (0.2, 5.0)]

    # Constraint: |beta_daily| >= 1.2 * |beta_milestone| -> -beta_daily >= -1.2 * beta_milestone
    constraints = [
        {'type': 'ineq', 'fun': lambda b: (-b[0]) - 1.2 * (-b[1])}
    ]

    res = minimize(loss, beta_init, method='SLSQP', jac=grad, bounds=bounds, constraints=constraints)

    # Verify optimizer convergence, bounds, ratio, and monotonicity constraints
    def validate_solution(res_obj) -> bool:
        if not getattr(res_obj, 'success', False) or getattr(res_obj, 'x', None) is None:
            return False
        b = np.asarray(res_obj.x, dtype=np.float64)
        if b.shape != (4,) or not np.all(np.isfinite(b)):
            return False
        tol = 1e-4
        for idx, (b_low, b_high) in enumerate(bounds):
            if b[idx] < b_low - tol or b[idx] > b_high + tol:
                return False
        # Constraint: |beta_daily| >= 1.2 * |beta_milestone|
        if (-b[0]) < 1.2 * (-b[1]) - tol:
            return False
        # Monotonicity constraints
        if not (b[0] < 0 and b[1] < 0 and b[2] > 0 and b[3] > 0):
            return False
        return True

    if not validate_solution(res):
        raise RuntimeError("Optimization failed: solver did not converge to a valid solution satisfying parameter bounds and ratio constraints")

    fitted_beta = res.x
    pred_probs = sigmoid(X @ fitted_beta)
    training_accuracy = float(np.mean((pred_probs >= 0.5) == (y == 1.0)))

    # Compute calibrated centroid weights from marginal utility ratios:
    # Daily utility vs Milestone utility
    daily_ratio = abs(fitted_beta[0]) / max(1e-5, abs(fitted_beta[1]))
    
    calibrated_weights = {
        'village': int(round(max(2, min(4, 2.0 * math.sqrt(daily_ratio))))),
        'ruined_portal': int(round(max(1, min(2, 1.0 * daily_ratio / 2.0)))),
        'trial_chamber': 2,
        'stronghold': 2,
        'mansion': 1,
        'ancient_city': 2,
        'desert_pyramid': 2,
        'jungle_temple': 2,
        'outpost': 1,
        'monument': 1,
        'shipwreck': 0,
        'mineshaft': 0
    }

    return {
        'fitted_beta': [round(float(b), 4) for b in fitted_beta],
        'feature_names': ['d_daily_scaled', 'd_milestone_scaled', 'a_build_scaled', 'r_diversity_scaled'],
        'daily_vs_milestone_utility_ratio': round(float(daily_ratio), 3),
        'training_accuracy': training_accuracy,
        'calibrated_centroid_weights': calibrated_weights,
        'recommendation': 'Research-only baseline; no production promotion without held-out cross-validation data',
        'promotion_eligible': False,
        'status': 'RESEARCH_ONLY'
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-pairs', type=Path, help='Path to custom pairwise preference JSON')
    parser.add_argument('--allow-demonstration-defaults', '--demo', action='store_true',
                        help='Explicitly allow using default synthetic demonstration pairs')
    parser.add_argument('--output', type=Path, required=True, help='Output calibration report path')
    args = parser.parse_args()

    if args.input_pairs is not None:
        if not args.input_pairs.exists():
            sys.exit(f"Error: Specified --input-pairs file does not exist: {args.input_pairs}")
        pairs = json.loads(args.input_pairs.read_text())
        data_provenance = 'custom_input_pairs'
    elif args.allow_demonstration_defaults:
        pairs = default_preference_pairs()
        data_provenance = 'synthetic_demonstration'
    else:
        sys.exit("Error: Missing --input-pairs. Missing input pairs must fail rather than silently falling back to defaults. To run demonstration baseline, specify --allow-demonstration-defaults (or --demo).")

    result = fit_bradley_terry(pairs)
    result['data_provenance'] = data_provenance
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(f"Calibration report written to: {args.output}")
    print(f"Fitted Beta: {result['fitted_beta']} | Training Accuracy: {result['training_accuracy'] * 100:.1f}%")
    print(f"Calibrated Weights: {result['calibrated_centroid_weights']}")


if __name__ == '__main__':
    main()
