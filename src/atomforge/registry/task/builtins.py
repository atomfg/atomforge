from atomforge.registry.task.manifest import TaskManifest

single_point_manifest = TaskManifest(
    kind="single_point",
    executor_cls="atomforge.task.singlepoint:SinglePointExecutor",
    spec_model="atomforge.task.singlepoint:SinglePoint",
    result_model="atomforge.task.singlepoint:SinglePointResult",
    capability_spec="atomforge.task.singlepoint:SinglePointCapabilitySpec",
    environment_factory_cls="atomforge.task.singlepoint:SinglePointEnvironmentFactory",
    distribution=["atomforge"],
)

bfgs_manifest = TaskManifest(
    kind="bfgs",
    executor_cls="atomforge.task.bfgs:BFGSExecutor",
    spec_model="atomforge.task.bfgs:BFGS",
    result_model="atomforge.task.bfgs:BFGSResult",
    capability_spec="atomforge.task.bfgs:BFGSCapabilitySpec",
    environment_factory_cls="atomforge.task.bfgs:BFGSEnvironmentFactory",
    distribution=["atomforge"],
)
