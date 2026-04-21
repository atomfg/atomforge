import pytest
from atomforge.registry.task.manifest import TaskManifest

@pytest.fixture
def manifest_factory():
    def factory(
    kind="single_point",
    executor_cls="atomforge.task.singlepoint:SinglePointExecutor",
    spec_model="atomforge.task.singlepoint:SinglePoint",
    result_model="atomforge.task.singlepoint:SinglePointResult",
    capability_spec="atomforge.task.singlepoint:SinglePointCapabilitySpec",
    environment_factory_cls="atomforge.task.singlepoint:SinglePointEnvironmentFactory",
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
