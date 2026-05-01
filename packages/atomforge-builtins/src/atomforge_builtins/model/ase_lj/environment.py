from atomforge_core.env.env import EnvironmentSpec
from atomforge_core.env.factory import DependencySummary, EnvironmentFactory

from atomforge_builtins.model.ase_lj.spec import LennardJones


class LennardJonesEnvironmentFactory(EnvironmentFactory[LennardJones]):
    dependency_summary = DependencySummary(
        base_requirements=("ase",),
        python="3.12",
    )

    def build(self, spec: LennardJones) -> EnvironmentSpec:
        return EnvironmentSpec(name=spec.kind, python="3.12", requirements=["ase"])
