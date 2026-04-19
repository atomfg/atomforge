import pytest
from atomforge.backend.subprocess.worker import SubprocessWorker
from atomforge.model.core.property import Property
from atomforge.registry.task.registry import TaskRegistry
from atomforge.model.registry import ModelRegistry
from atomforge.backend.base.resources import SystemResources, Availability
from atomforge.model.registry import register_lennard_jones
from atomforge.task.core.capability import TaskCapabilitySpec

def _register_single_point_task(registry: TaskRegistry) -> None:
    from atomforge.task.singlepoint import (
        SinglePointExecutor,
        SinglePointResult,
        SinglePoint,
        single_point_environment_factory
    )

    registry.register(
        task_kind="single_point",
        spec_model=SinglePoint,
        result_model=SinglePointResult,
        executor_class=SinglePointExecutor,
        capability_spec=TaskCapabilitySpec(
            required=frozenset(),
            optional=frozenset({Property.ENERGY, Property.FORCES}),
        ),
        environment_factory=single_point_environment_factory
    )


def simple_model_registry():
    registry = ModelRegistry()
    register_lennard_jones(registry)
    return registry

def simple_task_registry():
    registry = TaskRegistry()
    _register_single_point_task(registry)
    return registry


@pytest.fixture(scope="module")
def worker():

    task_registry = simple_task_registry()
    model_registry = simple_model_registry()
    system_resources = SystemResources(
        cpu_count=4,
        platform="test_platform",
        architecture="test_architecture",
        hostname="test_hostname",
        gpu_available=Availability.UNAVAILABLE,
    )

    worker = SubprocessWorker(
        stdin=None,
        stdout=None,
        stderr=None,
        name="test_worker",
        task_registry=task_registry,
        model_registry=model_registry,
        system_resources=system_resources,
    )
    return worker
