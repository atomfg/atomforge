from atomforge_core.env.env import EnvironmentSpec
from atomforge_core.env.factory import (
    DependencySummary,
    environment_factory_from_callable,
)

OptimizeEnvironmentFactory = environment_factory_from_callable(
    lambda spec: EnvironmentSpec(name="optimize", requirements=["ase"]),
    DependencySummary(base_requirements=["ase"]),
)
