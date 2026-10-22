"""Budget and dry-run checks; never launches a game server."""
import copy
import json
from pathlib import Path
import pytest

from scripts.predictor_targeted_bds import main, validate_cases

CASES = Path(__file__).resolve().parents[1] / 'reviews/storage-bds-verification-2026-10-20/CASES.json'


def cases():
    return json.loads(CASES.read_text())


def test_frozen_cases_fit_approved_cumulative_budgets():
    assert validate_cases(cases()) == dict(max_biome_reads=54, max_block_reads=3530, locate_commands=6)


@pytest.mark.parametrize('mutate', [
    lambda c: c.pop(),
    lambda c: c[0].update(seed='1'),
    lambda c: c[0]['points'][0].__setitem__(1, True),
    lambda c: c[0]['points'][0].__setitem__(1, 320),
    lambda c: c[0]['structures'][0].update(command_id='fortress'),
    lambda c: c[0]['points'].extend([[0, 63, 0]] * 70),
    lambda c: c[0]['structures'].extend([copy.deepcopy(c[0]['structures'][0])] * 33),
    lambda c: c[0]['columns'].extend([[i * 64, 4000] for i in range(10)]),
])
def test_invalid_or_oversized_request_fails_before_launch(mutate):
    data = cases()
    mutate(data)
    with pytest.raises(ValueError):
        validate_cases(data)


def test_default_is_read_only_dry_run(tmp_path, capsys, monkeypatch):
    import scripts.predictor_targeted_bds as module
    monkeypatch.setattr(module.subprocess, 'Popen', lambda *a, **k: pytest.fail('Game launch in dry run'))
    output = tmp_path / 'not-created'
    assert main(['--manifest', str(CASES), '--output', str(output)]) == 0
    assert not output.exists()
    assert json.loads(capsys.readouterr().out)['dry_run'] is True
