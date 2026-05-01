from atomforge_core.env.env import EnvironmentSpec
from atomforge_core.env.factory import (
    DependencySummary,
    environment_factory_from_callable,
)

AtomicDescriptorEnvironmentFactory = environment_factory_from_callable(
    lambda spec: EnvironmentSpec(name="atomic_descriptor"),
    DependencySummary(base_requirements=[]),
)
