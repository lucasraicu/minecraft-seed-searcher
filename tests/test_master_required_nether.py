import pytest

from seed_search.realm.baseline import evaluate_seed
from seed_search.realm.config import default_config, validate_config
from test_realm_baseline import FakeBackend


class NetherBackend(FakeBackend):
    missing = None
    calls = []

    def structure_pair(self, name, bounds):
        self.calls.append((name, bounds))
        if name == self.missing:
            return [], []
        return super().structure_pair(name, bounds)


@pytest.mark.parametrize('kind', ['fortress', 'bastion'])
def test_missing_either_final_nether_requirement_stays_pending(kind):
    class Missing(NetherBackend):
        missing = kind
        calls = []
    result = evaluate_seed(0, 12345, default_config(), backend_factory=Missing)
    assert result['counts']['confirmed_rejections'] == 0
    for candidate in result['anchors']:
        assert candidate['qualification'] == 'PENDING'
        assert 'final_' + kind in candidate['pending_reasons']
        assert set(candidate['required_nether_structures']) == {'fortress', 'bastion'}
        assert candidate['final_nether_prediction']['status'] == 'PENDING'
        assert candidate['final_nether_status'] == 'UNVERIFIED'
        assert candidate['required_nether_structures'][kind]['confirmed_absent'] is False


def test_nether_uses_each_exact_fractional_anchor_square_and_both_positive():
    class Positive(NetherBackend):
        calls = []
    result = evaluate_seed(0, -1, default_config(), backend_factory=Positive)
    for candidate in result['anchors']:
        assert candidate['qualification'] == 'PREDICTED'
        sx, sz = candidate['stronghold']
        assert candidate['bounds']['final_nether'] == [sx/8-448, sz/8-448, sx/8+448, sz/8+448]
        for kind in ('fortress', 'bastion'):
            record = candidate['required_nether_structures'][kind]
            assert record['bounds'] == candidate['bounds']['final_nether']
            assert record['predicted_viable']
        assert candidate['final_nether_prediction']['actual_generation_verified'] is False


def test_broad_fortress_does_not_substitute_for_final_square():
    class BroadOnly(FakeBackend):
        def structure_pair(self, name, bounds):
            if name == 'fortress':
                return [[1990, 1990]], [[1990, 1990]]
            return super().structure_pair(name, bounds)
    result = evaluate_seed(0, 42, default_config(), backend_factory=BroadOnly)
    assert result['counts']['initial_fortress_predicted'] == 1
    assert all('final_fortress' in row['pending_reasons'] for row in result['anchors'])


@pytest.mark.parametrize('required', [['fortress'], ['bastion'], [], ['bastion', 'fortress']])
def test_configuration_cannot_relax_nether_required_contract(required):
    cfg = default_config()
    cfg['structures']['nether_required'] = required
    with pytest.raises(ValueError, match='Fortress and Bastion'):
        validate_config(cfg)
