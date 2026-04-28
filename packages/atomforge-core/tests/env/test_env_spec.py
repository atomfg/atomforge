import pytest

from atomforge_core.env.env import EnvironmentSpec


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


def test_provider_requirements_are_normalized():
    env_spec = EnvironmentSpec(
        name="test-env",
        provider_requirements=(" Atomforge_Mace ", "atomforge-mace", "foo.bar"),
    )

    assert env_spec.provider_requirements == ("atomforge-mace", "foo.bar")


@pytest.mark.parametrize(
    "provider_requirement",
    [
        "atomforge-m3gnet>=1",
        "foo[bar]",
        "foo ; python_version<'3.12'",
        "foo @ file:///tmp/foo",
    ],
)
def test_provider_requirements_reject_non_name_syntax(provider_requirement: str):
    with pytest.raises(ValueError):
        EnvironmentSpec(
            name="test-env",
            provider_requirements=(provider_requirement,),
        )


def test_provider_requirements_reject_non_string_entries():
    with pytest.raises(TypeError):
        EnvironmentSpec(
            name="test-env",
            provider_requirements=("atomforge-core", 123),
        )


def test_provider_requirements_reject_single_string_input():
    with pytest.raises(TypeError):
        EnvironmentSpec(
            name="test-env",
            provider_requirements="atomforge-core",
        )


def test_requirements_still_accept_rich_requirement_strings():
    env_spec = EnvironmentSpec(
        name="test-env",
        requirements=(
            "foo[bar]",
            "foo @ file:///tmp/foo",
            "foo ; python_version<'3.12'",
        ),
    )

    assert env_spec.requirements == (
        "foo ; python_version<'3.12'",
        "foo @ file:///tmp/foo",
        "foo[bar]",
    )


def test_merge_provider_requirements_deduplicates_normalized_names():
    left = EnvironmentSpec(
        name="left",
        provider_requirements=("atomforge_mace",),
    )
    right = EnvironmentSpec(
        name="right",
        provider_requirements=("atomforge-mace",),
    )

    merged = left + right

    assert merged.provider_requirements == ("atomforge-mace",)

