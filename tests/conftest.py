"""Web contracts use a current private build, never an untracked historical artifact."""
import pytest


@pytest.fixture(scope='session')
def current_native_build(tmp_path_factory):
    from scripts.build_blueprint_batch import build
    directory=tmp_path_factory.mktemp('current-native-contracts')
    build(directory)
    return directory


@pytest.fixture(autouse=True)
def web_native_contract(request, monkeypatch):
    if request.module.__name__.startswith('test_web_'):
        from seed_search.web import server
        monkeypatch.setattr(server, 'DEFAULT_NATIVE_BUILD', request.getfixturevalue('current_native_build'))
