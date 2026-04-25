from atomforge_core.registry.task_manifest import TaskManifest

single_point_manifest = TaskManifest(
    kind="single_point",
    executor_cls="atomforge_builtins.task.singlepoint:SinglePointExecutor",
    spec_model="atomforge_builtins.task.singlepoint:SinglePoint",
    result_model="atomforge_builtins.task.singlepoint:SinglePointResult",
    capability_spec="atomforge_builtins.task.singlepoint:SinglePointCapabilitySpec",
    environment_factory_cls="atomforge_builtins.task.singlepoint:SinglePointEnvironmentFactory",
    distribution=["atomforge_builtins"],
)

bfgs_manifest = TaskManifest(
    kind="bfgs",
    executor_cls="atomforge_builtins.task.bfgs:BFGSExecutor",
    spec_model="atomforge_builtins.task.bfgs:BFGS",
    result_model="atomforge_builtins.task.bfgs:BFGSResult",
    capability_spec="atomforge_builtins.task.bfgs:BFGSCapabilitySpec",
    environment_factory_cls="atomforge_builtins.task.bfgs:BFGSEnvironmentFactory",
    distribution=["atomforge_builtins"],
)

batch_single_point_manifest = TaskManifest(
    kind="batch_single_point",
    executor_cls="atomforge_builtins.task.batch_singlepoint:BatchSinglePointExecutor",
    spec_model="atomforge_builtins.task.batch_singlepoint:BatchSinglePoint",
    result_model="atomforge_builtins.task.batch_singlepoint:BatchSinglePointResult",
    capability_spec="atomforge_builtins.task.batch_singlepoint:BatchSinglePointCapabilitySpec",
    environment_factory_cls="atomforge_builtins.task.batch_singlepoint:BatchSinglePointEnvironmentFactory",
    distribution=["atomforge_builtins"],
)