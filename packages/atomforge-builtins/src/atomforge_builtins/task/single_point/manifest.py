from atomforge_core.registry.task_manifest import TaskManifest

single_point_manifest = TaskManifest(
    kind="single_point",
    executor_cls="atomforge_builtins.task.single_point.executor:SinglePointExecutor",
    spec_model="atomforge_builtins.task.single_point.spec:SinglePoint",
    result_model="atomforge_builtins.task.single_point.result:SinglePointResult",
    capability_spec="atomforge_builtins.task.single_point.definitions:SinglePointCapabilitySpec",
    environment_factory_cls="atomforge_builtins.task.single_point.environment:SinglePointEnvironmentFactory",
    distribution=["atomforge_builtins"],
)
