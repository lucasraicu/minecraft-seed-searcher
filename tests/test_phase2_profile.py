"""Safety and interpretation contracts for the bounded diagnostic harness."""
import pytest
from scripts.profile_phase2 import validate_budget, summary, main, tree_bytes


@pytest.mark.parametrize('controls', [(True, 1, 1), (0, 1, 1), (16385, 1, 1),
                                      (1, 6, 1), (1, 1, 9), (16384, 3, 4)])
def test_profile_refuses_unbounded_or_invalid_work(controls):
    with pytest.raises(ValueError):
        validate_budget(*controls)


def test_default_profile_budget_is_bounded():
    assert validate_budget(8192, 3, 4) == 74012


def test_profile_never_overwrites_an_existing_output(tmp_path):
    sentinel = tmp_path / 'keep'
    sentinel.write_text('existing experiment')
    with pytest.raises(FileExistsError):
        main(['--output', str(tmp_path), '--build', str(tmp_path / 'unused')])
    assert sentinel.read_text() == 'existing experiment'


def test_summary_preserves_samples_and_uses_median():
    assert summary([1, 100, 2]) == {'samples': [1, 100, 2], 'median': 2,
                                     'minimum': 1, 'maximum': 100}
    with pytest.raises(ValueError):
        summary([])


def test_storage_measurement_includes_nested_files(tmp_path):
    (tmp_path / 'a').write_bytes(b'12')
    (tmp_path / 'nested').mkdir()
    (tmp_path / 'nested' / 'b').write_bytes(b'345')
    assert tree_bytes(tmp_path) == 5
