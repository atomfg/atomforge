import pytest
from atomforge.backend.subprocess.worker import SubprocessWorker
from atomforge.registry.task.registry import TaskRegistry
from atomforge.model.registry import ModelRegistry
from atomforge.backend.base.resources import SystemResources, Availability
from atomforge.model.registry import register_lennard_jones



def simple_model_registry():
    registry = ModelRegistry()
    register_lennard_jones(registry)
    return registry

def simple_task_registry():
    registry = TaskRegistry.default()
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
