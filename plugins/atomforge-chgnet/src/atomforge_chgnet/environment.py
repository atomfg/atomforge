from atomforge_core.env.env import EnvironmentSpec
from atomforge_core.env.factory import (
    DependencySummary,
    environment_factory_from_callable,
)


CHGNetEnvironmentFactory = environment_factory_from_callable(
    lambda spec: EnvironmentSpec(
        name=spec.kind,
        python=">=3.12",
        requirements=["chgnet", "ase"],
    ),
    DependencySummary(base_requirements=["chgnet", "ase"], python=">=3.12"),
)
