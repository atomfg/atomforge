from atomforge_core.env.env import EnvironmentSpec
from atomforge_core.env.factory import DependencySummary, EnvironmentFactory

from atomforge_m3gnet.definitions import REQUIREMENTS
from atomforge_m3gnet.spec import M3GNet


class M3GNetEnvironmentFactory(EnvironmentFactory[M3GNet]):
    dependency_summary = DependencySummary(
        base_requirements=tuple(REQUIREMENTS), python="3.10"
    )

    def build(self, spec: M3GNet) -> EnvironmentSpec:
        return EnvironmentSpec(
            name=spec.kind,
            python="3.10",
            requirements=REQUIREMENTS,
        )
