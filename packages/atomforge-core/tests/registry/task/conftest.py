import pytest

from atomforge_core.registry.task_manifest import TaskManifest


@pytest.fixture
def manifest_factory():
    def factory(
        kind="fake-task",
        executor_cls="atomforge_core.task.executor:TaskExecutor",
        spec_model="atomforge_core.task.spec:TaskSpec",
        result_model="atomforge_core.task.result:TaskResult",
        capability_spec="atomforge_core.task.capability:TaskCapabilitySpec",
        environment_factory_cls="atomforge_core.env.factory:EnvironmentFactory",
        distribution=["atomforge-core"],
    ):
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

