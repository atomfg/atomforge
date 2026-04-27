from atomforge_core.env.env import EnvironmentSpec
from atomforge_core.env.factory import (
    DependencySummary,
    environment_factory_from_callable,
)


MACEEnvironmentFactory = environment_factory_from_callable(
    lambda spec: EnvironmentSpec(
        name=spec.kind,
        python=">=3.12",
        requirements=["mace-torch", "torch"],
    ),
    DependencySummary(base_requirements=["mace-torch", "torch"], python=">=3.12"),
)
