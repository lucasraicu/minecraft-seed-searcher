"""Contract verification tests for truthful predictive verification and fail-closed calibration.

Tests mock external/native systems to verify:
1. Ground truth BDS verification contracts (Tier B skipped/unavailable/provision-only cannot certify).
2. Half-open 2048 window clipping and discovery scope preservation.
3. Backend resource lifecycle cleanup on all execution paths.
4. Fail-closed calibration contracts (bad inputs, optimizer failure, constraint violation).
5. Truthful training accuracy and research-only promotion gating.
6. Aggregated sampled-flat cell semantics and backward compatibility aliases.
"""
from dataclasses import dataclass
import math
from pathlib import Path
from typing import List, Tuple
from unittest.mock import MagicMock, patch
import numpy as np
import pytest

from scripts.bds_verify_finalist import verify_finalist
from scripts.calibrate_player_weights import (
    default_preference_pairs,
    fit_bradley_terry,
    main as calibrate_main,
)
from scripts.extract_player_metrics import extract_player_metrics
from seed_search.realm.structure_accuracy import (
    StrongholdIntegrity,
    VillageTopography,
    evaluate_finalist_accuracy,
)


# ---------------------------------------------------------------------------
# Helpers & Mocks
# ---------------------------------------------------------------------------

class StubBackend:
    """Mock Backend providing canned structure queries and heights."""

    def __init__(self, strongholds=None, villages=None, mansions=None, cities=None, chambers=None):
        self._strongholds = strongholds if strongholds is not None else [(100, 200)]
        self._villages = villages if villages is not None else [(50, 50)]
        self._mansions = mansions if mansions is not None else []
        self._cities = cities if cities is not None else []
        self._chambers = chambers if chambers is not None else []
        self.closed = False

    def structures(self, name: str, bounds: Tuple[int, int, int, int], viable: bool = True):
        if name == 'stronghold':
            return list(self._strongholds)
        elif name == 'village':
            return list(self._villages)
        elif name == 'mansion':
            return list(self._mansions)
        elif name == 'ancient_city':
            return list(self._cities)
        elif name == 'trial_chamber':
            return list(self._chambers)
        elif name == 'ruined_portal':
            return [(0, 0)]
        return []

    def stronghold_portal_details(self, x: int, z: int):
        return {
            'has_portal_room': True,
            'portal_eyes': 2,
            'bounding_box': [x - 10, 20, z - 10, x + 10, 40, z + 10],
            'valid_depth': True,
        }

    def heights(self, pts, vertical_step: int = 4):
        # Return surface height 70 (above water 63) with uniform flat grade
        n = len(pts)
        heights = np.full(n, 70, dtype=np.int32)
        biomes = np.full(n, 1, dtype=np.int32)
        return heights, biomes

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# ---------------------------------------------------------------------------
# Pillar 1: BDS Verification & Structure Accuracy Truthfulness Contracts
# ---------------------------------------------------------------------------

class TestBDSVerificationTruthfulness:

    def test_tier_b_skipped_cannot_certify(self):
        """When Docker is skipped, verdict must be PREDICTIVE_PASS, never CERTIFIED."""
        backend = StubBackend()
        report = verify_finalist(12345, cx=0, cz=0, skip_docker=True, backend=backend)

        assert report['tier_b_bds_ground_truth']['status'] == 'SKIPPED'
        assert report['final_verdict'] == 'PREDICTIVE_PASS'
        assert report['final_verdict'] != 'CERTIFIED'
        assert report['tier_a_predictive_accuracy']['certified'] is False
        assert report['tier_a_predictive_accuracy']['prediction_pass'] is True
        assert report['evidence_provenance'] == 'predictive_heuristics_tier_a_only'

    @patch('scripts.bds_verify_finalist.is_docker_available', return_value=False)
    def test_tier_b_unavailable_cannot_certify(self, mock_docker):
        """When Docker daemon is unavailable, status is UNAVAILABLE and never CERTIFIED."""
        backend = StubBackend()
        report = verify_finalist(12345, cx=0, cz=0, skip_docker=False, backend=backend)

        assert report['tier_b_bds_ground_truth']['status'] == 'UNAVAILABLE'
        assert report['final_verdict'] != 'CERTIFIED'
        assert report['final_verdict'] == 'PREDICTIVE_PASS'
        assert report['tier_a_predictive_accuracy']['certified'] is False

    @patch('scripts.bds_verify_finalist.is_docker_available', return_value=True)
    def test_tier_b_provision_only_cannot_certify(self, mock_docker):
        """When Docker info succeeds, status is PROVISION_ONLY and cannot claim image or certification."""
        backend = StubBackend()
        report = verify_finalist(12345, cx=0, cz=0, skip_docker=False, backend=backend)

        assert report['tier_b_bds_ground_truth']['status'] == 'PROVISION_ONLY'
        assert report['tier_b_bds_ground_truth']['block_verification'] == 'UNVERIFIED'
        assert report['final_verdict'] != 'CERTIFIED'
        assert report['final_verdict'] == 'PREDICTIVE_PASS'
        # Crucial: Must not claim BDS image is present
        assert 'not implemented' in report['tier_b_bds_ground_truth']['reason'].lower()

    def test_predictive_failed_verdict_when_tier_a_fails(self):
        """When Tier A integrity fails, verdict must be PREDICTIVE_FAILED."""
        # Stronghold without portal room
        backend = StubBackend()
        backend.stronghold_portal_details = lambda x, z: {
            'has_portal_room': False,
            'portal_eyes': 0,
            'bounding_box': [0, 0, 0, 0, 0, 0],
            'valid_depth': False,
        }
        report = verify_finalist(12345, cx=0, cz=0, skip_docker=True, backend=backend)

        assert report['tier_a_predictive_accuracy']['prediction_pass'] is False
        assert report['final_verdict'] == 'PREDICTIVE_FAILED'
        assert report['final_verdict'] != 'CERTIFIED'

    def test_stronghold_half_open_window_clipping_and_discovery_scope(self):
        """Strongholds discovered in wider bounds must be clipped to [cx-1024, cx+1024) x [cz-1024, cz+1024)."""
        # Center is (0, 0). Half-open window is [-1024, 1024) x [-1024, 1024).
        strongholds = [
            (0, 0),         # Inside window
            (-1024, -1024), # Boundary inside: -1024 is included
            (-1024, 500),   # Boundary inside: -1024 is included
            (1024, 0),      # Boundary outside: 1024 is excluded (half-open)
            (0, 1024),      # Boundary outside: 1024 is excluded
            (1500, 1500),   # Outside window (in discovery bounds 2048)
            (-1800, -500),  # Outside window (in discovery bounds 2048)
        ]
        villages = [
            (50, 50),       # Inside window
            (1024, 0),      # Boundary outside
            (-1024, 0),     # Boundary inside
        ]

        backend = StubBackend(strongholds=strongholds, villages=villages)
        report = verify_finalist(12345, cx=0, cz=0, skip_docker=True, backend=backend)

        counts = report['counts_in_window']
        discovery = report['discovery_scope']

        # Discovered strongholds = 7, window clipped strongholds = 3: (0,0), (-1024,-1024), (-1024, 500)
        assert discovery['discovered_strongholds_count'] == 7
        assert discovery['window_clipped_strongholds_count'] == 3
        assert counts['strongholds'] == 3

        # Villages clipped to half-open window: (50, 50) and (-1024, 0) -> 2
        assert counts['villages'] == 2

        # Strongholds passed to tier A evaluation must only be the 3 window-clipped ones
        assert report['tier_a_predictive_accuracy']['stronghold_count'] == 3

    @patch('scripts.bds_verify_finalist.Backend')
    def test_backend_lifecycle_closed_on_success(self, mock_backend_cls):
        """Backend must be cleanly closed after execution."""
        mock_instance = MagicMock()
        mock_instance.structures.return_value = []
        mock_backend_cls.return_value = mock_instance

        verify_finalist(12345, cx=0, cz=0, skip_docker=True)
        mock_instance.close.assert_called_once()

    @patch('scripts.bds_verify_finalist.Backend')
    def test_backend_lifecycle_closed_on_exception(self, mock_backend_cls):
        """Backend must be cleanly closed even when an exception occurs."""
        mock_instance = MagicMock()
        mock_instance.structures.side_effect = RuntimeError("Simulated failure")
        mock_backend_cls.return_value = mock_instance

        with pytest.raises(RuntimeError):
            verify_finalist(12345, cx=0, cz=0, skip_docker=True)

        mock_instance.close.assert_called_once()


class TestStructureAccuracyEvaluator:

    def test_evaluate_accuracy_window_filtering(self):
        """evaluate_finalist_accuracy respects optional half-open window bounds."""
        backend = StubBackend()
        strongholds = [(-1024, -1024), (1024, 1024), (0, 0)]
        villages = [(-1024, 0), (1024, 0), (100, 100)]
        window = (-1024, -1024, 1024, 1024)

        report = evaluate_finalist_accuracy(backend, strongholds, villages, window=window)
        # (1024, 1024) and (1024, 0) must be excluded
        assert report['stronghold_count'] == 2
        assert report['village_count'] == 2
        assert report['certified'] is False
        assert isinstance(report['prediction_pass'], bool)


# ---------------------------------------------------------------------------
# Pillar 2: Calibration Solver Fail-Closed & Truthfulness Contracts
# ---------------------------------------------------------------------------

class TestCalibrationContracts:

    def test_bad_inputs_empty_pairs(self):
        """Empty comparison pairs list must raise ValueError."""
        with pytest.raises(ValueError, match="non-empty list"):
            fit_bradley_terry([])

    def test_bad_inputs_invalid_feature_dimension(self):
        """Features with dimension != 4 must raise ValueError."""
        bad_pair = {
            'u_a': [100.0, 500.0, 1.0],  # 3 elements
            'u_b': [200.0, 500.0, 1.0, 0.5],
            'preferred': 'A',
            'weight': 1.0
        }
        with pytest.raises(ValueError, match="length 4"):
            fit_bradley_terry([bad_pair])

    def test_bad_inputs_non_finite_features(self):
        """NaN or inf features must raise ValueError."""
        nan_pair = {
            'u_a': [float('nan'), 500.0, 1.0, 0.5],
            'u_b': [200.0, 500.0, 1.0, 0.5],
            'preferred': 'A',
            'weight': 1.0
        }
        with pytest.raises(ValueError, match="finite numbers"):
            fit_bradley_terry([nan_pair])

        inf_pair = {
            'u_a': [100.0, 500.0, 1.0, 0.5],
            'u_b': [200.0, float('inf'), 1.0, 0.5],
            'preferred': 'A',
            'weight': 1.0
        }
        with pytest.raises(ValueError, match="finite numbers"):
            fit_bradley_terry([inf_pair])

    def test_bad_inputs_invalid_preference(self):
        """Preferred label other than 'A' or 'B' must raise ValueError."""
        bad_pref = {
            'u_a': [100.0, 500.0, 1.0, 0.5],
            'u_b': [200.0, 500.0, 1.0, 0.5],
            'preferred': 'TIE',
            'weight': 1.0
        }
        with pytest.raises(ValueError, match="preferred value"):
            fit_bradley_terry([bad_pref])

    def test_bad_inputs_invalid_weight(self):
        """Non-positive or non-finite sample weights must raise ValueError."""
        neg_weight = {
            'u_a': [100.0, 500.0, 1.0, 0.5],
            'u_b': [200.0, 500.0, 1.0, 0.5],
            'preferred': 'A',
            'weight': -0.5
        }
        with pytest.raises(ValueError, match="Sample weight must be a positive finite number"):
            fit_bradley_terry([neg_weight])

        zero_weight = {
            'u_a': [100.0, 500.0, 1.0, 0.5],
            'u_b': [200.0, 500.0, 1.0, 0.5],
            'preferred': 'A',
            'weight': 0.0
        }
        with pytest.raises(ValueError, match="Sample weight must be a positive finite number"):
            fit_bradley_terry([zero_weight])

    def test_bad_inputs_invalid_l2_reg(self):
        """Negative or non-finite l2_reg must raise ValueError."""
        pairs = default_preference_pairs()
        with pytest.raises(ValueError, match="l2_reg"):
            fit_bradley_terry(pairs, l2_reg=-0.01)

        with pytest.raises(ValueError, match="l2_reg"):
            fit_bradley_terry(pairs, l2_reg=float('nan'))

    @patch('scripts.calibrate_player_weights.minimize')
    def test_optimizer_failure_fails_closed(self, mock_minimize):
        """Optimizer non-convergence must fail closed with RuntimeError."""
        res = MagicMock()
        res.success = False
        res.x = np.array([-1.5, -0.6, 1.0, 1.2])
        mock_minimize.return_value = res

        pairs = default_preference_pairs()
        with pytest.raises(RuntimeError, match="Optimization failed"):
            fit_bradley_terry(pairs)

    @patch('scripts.calibrate_player_weights.minimize')
    def test_optimizer_bound_violation_fails_closed(self, mock_minimize):
        """Fitted parameters violating variable bounds must fail closed."""
        res = MagicMock()
        res.success = True
        # beta_daily is positive (+1.0), violating bounds [-5.0, -0.2]
        res.x = np.array([1.0, -0.6, 1.0, 1.2])
        mock_minimize.return_value = res

        pairs = default_preference_pairs()
        with pytest.raises(RuntimeError, match="Optimization failed"):
            fit_bradley_terry(pairs)

    @patch('scripts.calibrate_player_weights.minimize')
    def test_optimizer_ratio_constraint_violation_fails_closed(self, mock_minimize):
        """Fitted parameters violating |beta_daily| >= 1.2 * |beta_milestone| must fail closed."""
        res = MagicMock()
        res.success = True
        # |-0.5| < 1.2 * |-1.0| (0.5 < 1.2)
        res.x = np.array([-0.5, -1.0, 1.0, 1.2])
        mock_minimize.return_value = res

        pairs = default_preference_pairs()
        with pytest.raises(RuntimeError, match="Optimization failed"):
            fit_bradley_terry(pairs)

    def test_truthful_output_keys_and_research_only_status(self):
        """Fitted result must report training_accuracy (not cross-validation) and research-only status."""
        pairs = default_preference_pairs()
        result = fit_bradley_terry(pairs)

        assert 'training_accuracy' in result
        assert 'cross_validation_accuracy' not in result
        assert 0.0 <= result['training_accuracy'] <= 1.0
        assert result['status'] == 'RESEARCH_ONLY'
        assert result['promotion_eligible'] is False
        assert 'held-out cross-validation' in result['recommendation']

        # Check parameter constraints on actual fit
        beta = result['fitted_beta']
        assert beta[0] < 0  # beta_daily < 0
        assert beta[1] < 0  # beta_milestone < 0
        assert beta[2] > 0  # beta_build > 0
        assert beta[3] > 0  # beta_diversity > 0
        assert abs(beta[0]) >= 1.2 * abs(beta[1]) - 1e-5

    def test_cli_missing_input_pairs_fails_without_demo_flag(self):
        """CLI invocation without --input-pairs must fail rather than silently using defaults."""
        with patch('sys.argv', ['calibrate_player_weights.py', '--output', '/tmp/dummy_out.json']):
            with pytest.raises(SystemExit) as exc_info:
                calibrate_main()
            assert "Missing --input-pairs" in str(exc_info.value)

    def test_cli_explicit_nonexistent_input_pairs_fails(self):
        """CLI invocation with nonexistent --input-pairs file must fail."""
        with patch('sys.argv', ['calibrate_player_weights.py', '--input-pairs', '/tmp/nonexistent_file_xyz.json', '--output', '/tmp/dummy_out.json']):
            with pytest.raises(SystemExit) as exc_info:
                calibrate_main()
            assert "does not exist" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Pillar 3: Offline Metric Extractor Semantics
# ---------------------------------------------------------------------------

class TestExtractPlayerMetricsSemantics:

    def test_sampled_flat_cells_metadata_and_backward_compatibility(self):
        """Extractor must describe aggregated sampled-flat cells, maintaining compatibility aliases."""
        backend = StubBackend()
        metrics = extract_player_metrics(backend, cx=0, cz=0, num_players=20)

        terrain = metrics['terrain_metrics']
        # Semantics metadata
        assert terrain['metric_type'] == 'square_aggregated_sampled_flat_cells'
        assert 'sampled_flat_cells_count' in terrain
        assert 'total_sampled_cells' in terrain
        assert 'sampled_flat_cell_hectares' in terrain
        assert 'sampled_flat_fraction' in terrain

        # Backward compatibility aliases
        assert terrain['flat_buildable_hectares'] == terrain['sampled_flat_cell_hectares']
        assert terrain['flat_fraction_near_spawn'] == terrain['sampled_flat_fraction']

        # Production utility vector integrity (4-dimensional: daily, milestone, buildable, diversity)
        u_vec = metrics['utility_vector']
        assert len(u_vec) == 4
        assert u_vec[2] == terrain['flat_buildable_hectares']


def test_unknown_prediction_is_not_a_failed_or_verified_observation(monkeypatch):
    import scripts.bds_verify_finalist as module
    monkeypatch.setattr(module, 'evaluate_finalist_accuracy', lambda *args: {})
    report = module.verify_finalist(1, 0, 0, skip_docker=True, backend=StubBackend())
    assert report['final_verdict'] == 'UNKNOWN'
    assert report['evidence']['generated_blocks_verified'] is False
    assert report['evidence']['observed_game_build'] is None


def test_optimizer_column_vector_is_rejected(monkeypatch):
    from types import SimpleNamespace
    import scripts.calibrate_player_weights as module
    monkeypatch.setattr(module, 'minimize', lambda *args, **kwargs:
                        SimpleNamespace(success=True, x=np.array([[-2.], [-1.], [1.], [1.]])))
    with pytest.raises(RuntimeError, match='valid solution'):
        module.fit_bradley_terry(module.default_preference_pairs())
