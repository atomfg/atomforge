from atomforge_core.registry.task_manifest import TaskManifest

batch_single_point_manifest = TaskManifest(
    kind="batch_single_point",
    executor_cls="atomforge_builtins.task.batch_single_point.executor:BatchSinglePointExecutor",
    spec_model="atomforge_builtins.task.batch_single_point.spec:BatchSinglePoint",
    result_model="atomforge_builtins.task.batch_single_point.result:BatchSinglePointResult",
    capability_spec="atomforge_builtins.task.batch_single_point.definitions:BatchSinglePointCapabilitySpec",
    environment_factory_cls="atomforge_builtins.task.batch_single_point.environment:BatchSinglePointEnvironmentFactory",
    distribution=["atomforge_builtins"],
)
