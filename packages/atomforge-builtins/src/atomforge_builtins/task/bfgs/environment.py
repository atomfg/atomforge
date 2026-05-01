from atomforge_core.env.env import EnvironmentSpec
from atomforge_core.env.factory import (
    DependencySummary,
    environment_factory_from_callable,
)

BFGSEnvironmentFactory = environment_factory_from_callable(
    lambda spec: EnvironmentSpec(name="bfgs", requirements=["ase"]),
    DependencySummary(base_requirements=["ase"]),
)
