from atomforge_core.registry.task_manifest import TaskManifest

_PACKAGE = "atomforge_builtins.task.describe_model_result"

describe_model_result_manifest = TaskManifest(
    kind="describe_model_result",
    executor_cls=f"{_PACKAGE}.executor:DescribeModelResultExecutor",
    spec_model=f"{_PACKAGE}.spec:DescribeModelResult",
    result_model=f"{_PACKAGE}.result:DescribeModelResultResult",
    capability_spec=f"{_PACKAGE}.definitions:DescribeModelResultCapabilitySpec",
    environment_factory_cls=(
        f"{_PACKAGE}.environment:DescribeModelResultEnvironmentFactory"
    ),
    distribution=["atomforge_builtins"],
)
