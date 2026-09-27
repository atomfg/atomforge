from atomforge_core.env.env import EnvironmentSpec
from atomforge_core.env.factory import DependencySummary, EnvironmentFactory

from atomforge_builtins.model.ase_lj.spec import LennardJones

TESTED_REQUIREMENTS = ("ase==3.29.0",)
LATEST_REQUIREMENTS = ("ase>=3.29.0",)
ENVIRONMENT_PROFILES = {
    "tested": EnvironmentSpec(
        name="ase-lj", python="==3.12.*", requirements=TESTED_REQUIREMENTS
    ),
    "latest": EnvironmentSpec(
        name="ase-lj", python=">=3.12", requirements=LATEST_REQUIREMENTS
    ),
}


class LennardJonesEnvironmentFactory(EnvironmentFactory[LennardJones]):
    dependency_summary = DependencySummary(
        possible_requirements=TESTED_REQUIREMENTS + LATEST_REQUIREMENTS,
        possible_python=("==3.12.*", ">=3.12"),
    )

    def build(self, spec: LennardJones) -> EnvironmentSpec:
        return ENVIRONMENT_PROFILES[spec.environment_profile]
