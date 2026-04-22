import pytest 

from atomforge.backend.subprocess.backend import SubprocessBackend
from atomforge.settings.settings import AtomforgeSettings
from pathlib import Path

@pytest.fixture(scope="session")
def settings(tmpdir_factory) -> AtomforgeSettings:
    root_env_dir = Path(tmpdir_factory.mktemp("envs"))
    return AtomforgeSettings(env_search_paths=[root_env_dir], env_install_path=root_env_dir)    

@pytest.fixture(scope="module")
def backend(settings):
    backend = SubprocessBackend(settings=settings)
    yield backend
    backend.shutdown()