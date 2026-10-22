"""Tests for Pillar 2: player utility metrics and Bradley-Terry calibration."""
import pytest
from seed_search.backend import Backend
from scripts.extract_player_metrics import extract_player_metrics
from scripts.calibrate_player_weights import default_preference_pairs, fit_bradley_terry


def test_extract_player_metrics_structure_and_bounds():
    with Backend(12345) as b:
        metrics = extract_player_metrics(b, 0, 0, num_players=20)
    
    assert 'center' in metrics
    assert 'commute_metrics' in metrics
    assert 'terrain_metrics' in metrics
    assert 'multiplayer_metrics' in metrics
    assert 'utility_vector' in metrics
    
    commute = metrics['commute_metrics']
    assert commute['d_daily_index'] >= 0.0
    assert commute['d_milestone_index'] >= 0.0
    
    terrain = metrics['terrain_metrics']
    assert terrain['flat_buildable_hectares'] >= 0.0
    assert 0.0 <= terrain['flat_fraction_near_spawn'] <= 1.0
    assert terrain['metric_type'] == 'square_aggregated_sampled_flat_cells'
    assert 'sampled_flat_cells_count' in terrain
    
    mp = metrics['multiplayer_metrics']
    assert mp['target_players'] == 20
    assert 0.0 <= mp['resource_diversity_index'] <= 1.0
    
    u = metrics['utility_vector']
    assert len(u) == 4


def test_bradley_terry_calibration_fits_valid_weights():
    pairs = default_preference_pairs()
    assert len(pairs) >= 5
    
    result = fit_bradley_terry(pairs)
    assert 'fitted_beta' in result
    assert len(result['fitted_beta']) == 4
    
    beta = result['fitted_beta']
    # beta_daily < 0
    assert beta[0] < 0
    # beta_milestone < 0
    assert beta[1] < 0
    # Daily penalty is stronger than milestone penalty: |beta_daily| >= 1.2 * |beta_milestone|
    assert abs(beta[0]) >= 1.2 * abs(beta[1]) - 1e-5
    # Buildable land reward > 0
    assert beta[2] > 0
    # Resource diversity reward > 0
    assert beta[3] > 0
    
    assert result['training_accuracy'] >= 0.80
    assert result['status'] == 'RESEARCH_ONLY'
    assert result['promotion_eligible'] is False
    assert 'calibrated_centroid_weights' in result
    weights = result['calibrated_centroid_weights']
    assert weights['village'] >= 2
    assert weights['stronghold'] >= 1

