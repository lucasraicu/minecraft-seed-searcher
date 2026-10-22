import importlib.util
from pathlib import Path
import pytest

path=Path(__file__).resolve().parents[2]/'scripts/catalog_reference.py'
spec=importlib.util.spec_from_file_location('catalog_reference_test',path)
cli=importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)


@pytest.mark.parametrize('threads,seconds',[(0,300),(5,300),(True,300),(1,0),(1,301),(1,1.5)])
def test_resource_budget_rejects_expansion(threads,seconds):
    with pytest.raises(ValueError): cli.validate_budget(threads,seconds)


def test_atomic_checkpoint_roundtrip_and_failure(tmp_path):
    path=tmp_path/'checkpoint.json'
    cli.atomic_json(path,{'seed':'-9223372036854775808'})
    assert path.read_text()=='{"seed":"-9223372036854775808"}'
    with pytest.raises(ValueError): cli.atomic_json(path,{'bad':float('nan')})
    assert path.read_text()=='{"seed":"-9223372036854775808"}'
    assert len(list(tmp_path.iterdir()))==1
