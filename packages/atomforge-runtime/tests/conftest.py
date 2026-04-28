from io import StringIO

import pytest

from atomforge_core.structure import StructureData
from atomforge_runtime.backend.subprocess.worker import SubprocessWorker
from atomforge_runtime.resources import Availability, SystemResources

from runtime_fakes import build_model_registry
from runtime_fakes import build_task_registry


@pytest.fixture(scope="module")
def example_structure():
    return StructureData(
        positions=[[4.5, 0, 0], [5.5, 0, 0]],
        cell=[[10, 0, 0], [0, 10, 0], [0, 0, 10]],
        numbers=[1, 8],
        pbc=[False, False, False],
    )


def _system_resources() -> SystemResources:
    return SystemResources(
        cpu_count=4,
        platform="test_platform",
        architecture="test_architecture",
        hostname="test_hostname",
        gpu_available=Availability.UNAVAILABLE,
    )


@pytest.fixture(scope="module")
def worker():
    return SubprocessWorker(
        stdin=None,
        stdout=None,
        stderr=None,
        name="test_worker",
        task_registry=build_task_registry(),
        model_registry=build_model_registry(),
        system_resources=_system_resources(),
    )


@pytest.fixture
def run_worker():
    def internal(input_text: str):
        stdin = StringIO(input_text)
        stdout = StringIO()
        stderr = StringIO()
        worker = SubprocessWorker(
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            name="test_worker",
            task_registry=build_task_registry(),
            model_registry=build_model_registry(),
            system_resources=_system_resources(),
        )
        exit_code = worker.run()
        return exit_code, stdout.getvalue(), stderr.getvalue()

    return internal
