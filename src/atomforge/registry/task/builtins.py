from atomforge.registry.task.manifest import TaskManifest

single_point_manifest = TaskManifest(
    kind="single_point",
    executor_class="atomforge.task.singlepoint:SinglePointExecutor",
    spec_model="atomforge.task.singlepoint:SinglePoint",
    result_model="atomforge.task.singlepoint:SinglePointResult",
    capability_spec="atomforge.task.singlepoint:SinglePointCapabilitySpec",
    environment_factory="atomforge.task.singlepoint:single_point_environment_factory",
    )

bfgs_manifest = TaskManifest(
    kind="bfgs",
    executor_class="atomforge.task.bfgs:BFGSExecutor",
    spec_model="atomforge.task.bfgs:BFGS",
    result_model="atomforge.task.bfgs:BFGSResult",
    capability_spec="atomforge.task.bfgs:BFGSCapabilitySpec",
    environment_factory="atomforge.task.bfgs:bfgs_environment_factory",
    )