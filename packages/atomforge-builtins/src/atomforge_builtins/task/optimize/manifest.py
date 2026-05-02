from atomforge_core.registry.task_manifest import TaskManifest

optimize_manifest = TaskManifest(
    kind="optimize",
    executor_cls="atomforge_builtins.task.optimize.executor:OptimizeExecutor",
    spec_model="atomforge_builtins.task.optimize.spec:Optimize",
    result_model="atomforge_builtins.task.optimize.result:OptimizeResult",
    capability_spec="atomforge_builtins.task.optimize.definitions:OptimizeCapabilitySpec",
    environment_factory_cls="atomforge_builtins.task.optimize.environment:OptimizeEnvironmentFactory",
    distribution=["atomforge_builtins"],
)
