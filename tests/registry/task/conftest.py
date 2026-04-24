import pytest
from atomforge._core.registry.task_manifest import TaskManifest

@pytest.fixture
def manifest_factory():
    def factory(
    kind="single_point",
    executor_cls="atomforge._builtins.task.singlepoint:SinglePointExecutor",
    spec_model="atomforge._builtins.task.singlepoint:SinglePoint",
    result_model="atomforge._builtins.task.singlepoint:SinglePointResult",
    capability_spec="atomforge._builtins.task.singlepoint:SinglePointCapabilitySpec",
    environment_factory_cls="atomforge._builtins.task.singlepoint:SinglePointEnvironmentFactory",
    distribution=["atomforge"]):
        return TaskManifest(
            kind=kind,
            spec_model=spec_model,
            executor_cls=executor_cls,
            result_model=result_model,
            capability_spec=capability_spec,
            environment_factory_cls=environment_factory_cls,
            distribution=distribution,
        )
    return factory
