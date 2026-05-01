import pytest

from atomforge_core.registry.task_manifest import TaskManifest
from atomforge_runtime.registry.task.task_registry import TaskRegistry


def test_task_manifest_builtin_registry_loads_tasks():
    registry = TaskRegistry.strict()
    assert registry.get("single_point").spec_model.__name__ == "SinglePoint"


@pytest.fixture
def manifest_factory():
    def factory(
        kind="single_point",
        executor_cls="atomforge_builtins.task.single_point.executor:SinglePointExecutor",
        spec_model="atomforge_builtins.task.single_point.spec:SinglePoint",
        result_model="atomforge_builtins.task.single_point.result:SinglePointResult",
        capability_spec="atomforge_builtins.task.single_point.definitions:SinglePointCapabilitySpec",
        environment_factory_cls="atomforge_builtins.task.single_point.environment:SinglePointEnvironmentFactory",
        distribution=["atomforge-builtins"],
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


def test_task_manifest_factory_default(manifest_factory):
    manifest = manifest_factory()
    assert isinstance(manifest, TaskManifest)
