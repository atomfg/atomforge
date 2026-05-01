from atomforge_core.env.env import EnvironmentSpec
from atomforge_core.env.factory import (
    DependencySummary,
    environment_factory_from_callable,
)

SinglePointEnvironmentFactory = environment_factory_from_callable(
    lambda spec: EnvironmentSpec(name="single_point"),
    DependencySummary(base_requirements=[]),
)
