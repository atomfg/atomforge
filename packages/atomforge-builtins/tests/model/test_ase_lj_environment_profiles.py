import pytest
from pydantic import ValidationError

from atomforge_builtins.model.ase_lj.environment import (
    ENVIRONMENT_PROFILES,
    LennardJonesEnvironmentFactory,
)
from atomforge_builtins.model.ase_lj.spec import LennardJones


@pytest.mark.parametrize("profile", ["tested", "latest"])
def test_lennard_jones_environment_profiles_are_deterministic(profile):
    factory = LennardJonesEnvironmentFactory()
    spec = LennardJones(environment_profile=profile)

    assert factory(spec) == factory(spec) == ENVIRONMENT_PROFILES[profile]


def test_lennard_jones_profile_constraints():
    factory = LennardJonesEnvironmentFactory()

    tested = factory(LennardJones(environment_profile="tested"))
    latest = factory(LennardJones(environment_profile="latest"))

    assert tested.python == "==3.12.*"
    assert tested.requirements == ("ase==3.29.0",)
    assert latest.python == ">=3.12"
    assert latest.requirements == ("ase>=3.29.0",)


def test_lennard_jones_rejects_unknown_environment_profile():
    with pytest.raises(ValidationError):
        LennardJones(environment_profile="unsupported")
