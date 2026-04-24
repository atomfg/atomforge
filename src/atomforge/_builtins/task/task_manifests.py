from atomforge._core.registry.task_manifest import TaskManifest

single_point_manifest = TaskManifest(
    kind="single_point",
    executor_cls="atomforge._builtins.task.singlepoint:SinglePointExecutor",
    spec_model="atomforge._builtins.task.singlepoint:SinglePoint",
    result_model="atomforge._builtins.task.singlepoint:SinglePointResult",
    capability_spec="atomforge._builtins.task.singlepoint:SinglePointCapabilitySpec",
    environment_factory_cls="atomforge._builtins.task.singlepoint:SinglePointEnvironmentFactory",
    distribution=["atomforge"],
)

bfgs_manifest = TaskManifest(
    kind="bfgs",
    executor_cls="atomforge._builtins.task.bfgs:BFGSExecutor",
    spec_model="atomforge._builtins.task.bfgs:BFGS",
    result_model="atomforge._builtins.task.bfgs:BFGSResult",
    capability_spec="atomforge._builtins.task.bfgs:BFGSCapabilitySpec",
    environment_factory_cls="atomforge._builtins.task.bfgs:BFGSEnvironmentFactory",
    distribution=["atomforge"],
)

batch_single_point_manifest = TaskManifest(
    kind="batch_single_point",
    executor_cls="atomforge._builtins.task.batch_singlepoint:BatchSinglePointExecutor",
    spec_model="atomforge._builtins.task.batch_singlepoint:BatchSinglePoint",
    result_model="atomforge._builtins.task.batch_singlepoint:BatchSinglePointResult",
    capability_spec="atomforge._builtins.task.batch_singlepoint:BatchSinglePointCapabilitySpec",
    environment_factory_cls="atomforge._builtins.task.batch_singlepoint:BatchSinglePointEnvironmentFactory",
    distribution=["atomforge"],
)