from atomforge_core.env.env import EnvironmentSpec
from atomforge_core.env.factory import (
    DependencySummary,
    environment_factory_from_callable,
)

# No requirements, so the task runs in the model's own environment (the
# environment name is not part of its hash).
DescribeModelResultEnvironmentFactory = environment_factory_from_callable(
    lambda spec: EnvironmentSpec(name="describe_model_result"),
    DependencySummary(base_requirements=[]),
)
