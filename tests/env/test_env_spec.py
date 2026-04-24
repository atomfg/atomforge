import pytest
from atomforge._core.env.env import EnvironmentSpec

@pytest.fixture
def env_spec() -> EnvironmentSpec:
    return EnvironmentSpec(
        name="test-env",
        python="3.8",
        requirements=("numpy==1.22", "pandas"),
        channels=("conda-forge",),
        extras={"dev": "pytest"},
    )

def test_hash(env_spec: EnvironmentSpec):
    hash_value = env_spec.hash()
    assert isinstance(hash_value, str)
    assert len(hash_value) == 64

def test_short_hash(env_spec: EnvironmentSpec):
    short_hash_value = env_spec.short_hash()
    assert isinstance(short_hash_value, str)
    assert len(short_hash_value) == 16

def test_name_with_hash(env_spec: EnvironmentSpec):
    name_with_hash = env_spec.name_with_hash()
    assert name_with_hash.startswith(env_spec.name)
    assert name_with_hash.endswith(env_spec.short_hash())

def test_merge_requirements(env_spec: EnvironmentSpec):
    other_requirements = ("scipy", "numpy")
    merged = env_spec.merge_requirements(env_spec.requirements, other_requirements)
    assert set(merged) == {"numpy", "pandas", "scipy"}

def test_merge_channels(env_spec: EnvironmentSpec):
    other_channels = ("defaults", "conda-forge")
    merged = env_spec.merge_channels(env_spec.channels, other_channels)
    assert set(merged) == {"conda-forge", "defaults"}

def test_merge_python(env_spec: EnvironmentSpec):
    assert env_spec.merge_python("3.8", "3.8") == "3.8"
    assert env_spec.merge_python("3.8", None) == "3.8"
    assert env_spec.merge_python(None, "3.8") == "3.8"
    with pytest.raises(ValueError):
        env_spec.merge_python("3.8", "3.9")

def test_merge_requirements_conflict(env_spec: EnvironmentSpec):
    with pytest.raises(ValueError):
        env_spec.merge_requirements(env_spec.requirements, ("numpy==1.19",))

def test_merge_requirements_no_conflict(env_spec: EnvironmentSpec):
    merged = env_spec.merge_requirements(env_spec.requirements, ("pandas==1.22",))
    assert set(merged) == {"numpy==1.22", "pandas==1.22"}

def test_merge_extras(env_spec: EnvironmentSpec):
    extras1 = {"dev": "pytest", "docs": "sphinx"}
    extras2 = {"dev": "pytest", "ci": "tox"}
    merged = env_spec.extras_merge(extras1, extras2)
    assert merged == {"dev": "pytest", "docs": "sphinx", "ci": "tox"}

def test_merge_extras_conflict(env_spec: EnvironmentSpec):
    extras1 = {"dev": "pytest"}
    extras2 = {"dev": "tox"}
    with pytest.raises(ValueError):
        env_spec.extras_merge(extras1, extras2)