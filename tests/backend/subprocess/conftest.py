import pytest
from atomforge_runtime.backend.subprocess.worker import SubprocessWorker
from atomforge_runtime.registry.task.task_registry import TaskRegistry
from atomforge_runtime.registry.model.model_registry import ModelRegistry
from atomforge_runtime.resources import SystemResources, Availability
from io import StringIO


def simple_model_registry():
    return ModelRegistry.default()

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

@pytest.fixture()
def run_worker():
    def internal(input: str):
        task_registry = simple_task_registry()
        model_registry = simple_model_registry()
        system_resources = SystemResources(
            cpu_count=4,
            platform="test_platform",
            architecture="test_architecture",
            hostname="test_hostname",
            gpu_available=Availability.UNAVAILABLE,
        )

        stdin = StringIO(input)
        stdout = StringIO()
        stderr = StringIO()

        worker = SubprocessWorker(
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            name="test_worker",
            task_registry=task_registry,
            model_registry=model_registry,
            system_resources=system_resources,
        )
        exit_code = worker.run()
        return exit_code, stdout.getvalue(), stderr.getvalue()
    return internal