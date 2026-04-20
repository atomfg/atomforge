import pytest
from atomforge.registry.task.manifest import TaskManifest

@pytest.fixture
def manifest_factory():
    def factory(
    kind="single_point",
    executor_class="atomforge.task.singlepoint:SinglePointExecutor",
    spec_model="atomforge.task.singlepoint:SinglePoint",
    result_model="atomforge.task.singlepoint:SinglePointResult",
    capability_spec="atomforge.task.singlepoint:SinglePointCapabilitySpec",
    environment_factory="atomforge.task.singlepoint:single_point_environment_factory",
    distribution=["atomforge"]):
        return TaskManifest(
            kind=kind,
            spec_model=spec_model,
            executor_class=executor_class,
            result_model=result_model,
            capability_spec=capability_spec,
            environment_factory=environment_factory,
            distribution=distribution,
        )
    return factory
