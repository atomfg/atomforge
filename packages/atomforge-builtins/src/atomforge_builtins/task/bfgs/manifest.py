from atomforge_core.registry.task_manifest import TaskManifest

bfgs_manifest = TaskManifest(
    kind="bfgs",
    executor_cls="atomforge_builtins.task.bfgs.executor:BFGSExecutor",
    spec_model="atomforge_builtins.task.bfgs.spec:BFGS",
    result_model="atomforge_builtins.task.bfgs.result:BFGSResult",
    capability_spec="atomforge_builtins.task.bfgs.definitions:BFGSCapabilitySpec",
    environment_factory_cls="atomforge_builtins.task.bfgs.environment:BFGSEnvironmentFactory",
    distribution=["atomforge_builtins"],
)
