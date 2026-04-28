import pytest

from atomforge_core.resources.resource_caps import ResourceCapabilities
from atomforge_core.resources.resource_models import ExecutionResources
from atomforge_core.resources.resource_probes import ProbeResult
from atomforge_runtime.resources import Availability, SystemResources, resolve_accelerator


@pytest.fixture
def default_exec_resources() -> ExecutionResources:
    return ExecutionResources(strict=False)


@pytest.fixture
def gpu_exec_resources() -> ExecutionResources:
    return ExecutionResources(accelerator="gpu", strict=False)


@pytest.fixture
def gpu_exec_resources_strict() -> ExecutionResources:
    return ExecutionResources(accelerator="gpu", strict=True)


@pytest.fixture
def gpu_cpu_probe() -> ProbeResult:
    return ProbeResult(available_accelerators=["gpu", "cpu"])


@pytest.fixture
def gpu_unavailable_probe() -> ProbeResult:
    return ProbeResult(available_accelerators=["cpu"])


@pytest.fixture(
    params=[Availability.UNAVAILABLE, Availability.UNKNOWN, Availability.AVAILABLE]
)
def system_resources(request) -> SystemResources:
    return SystemResources(
        cpu_count=8,
        platform="Linux",
        architecture="x86_64",
        hostname="test-machine",
        gpu_available=request.param,
    )


def test_gpu_exec_resources_no_probe(gpu_exec_resources, system_resources):
    resource_caps = ResourceCapabilities(accelerator=["gpu", "cpu"])
    resolved = resolve_accelerator(
        exec_resources=gpu_exec_resources,
        resource_caps=resource_caps,
        system_resources=system_resources,
        probe_result=None,
        messages={},
    )

    if system_resources.gpu_available == Availability.AVAILABLE:
        assert resolved == "gpu"
    else:
        assert resolved == "cpu"


def test_gpu_downgrade_model_incapable(gpu_exec_resources, system_resources):
    resource_caps = ResourceCapabilities(accelerator=["cpu"])
    resolved = resolve_accelerator(
        exec_resources=gpu_exec_resources,
        resource_caps=resource_caps,
        system_resources=system_resources,
        probe_result=None,
        messages={},
    )

    assert resolved == "cpu"


def test_resource_resolution_gpu_exec_probe(
    gpu_exec_resources, gpu_cpu_probe, system_resources
):
    resource_caps = ResourceCapabilities(accelerator=["gpu", "cpu"])
    resolved = resolve_accelerator(
        exec_resources=gpu_exec_resources,
        resource_caps=resource_caps,
        system_resources=system_resources,
        probe_result=gpu_cpu_probe,
        messages={},
    )

    assert resolved == "gpu"


def test_default_resources(default_exec_resources, system_resources):
    resource_caps = ResourceCapabilities(accelerator=["gpu", "cpu"])
    resolved = resolve_accelerator(
        exec_resources=default_exec_resources,
        resource_caps=resource_caps,
        system_resources=system_resources,
        probe_result=None,
        messages={},
    )

    if system_resources.gpu_available == Availability.AVAILABLE:
        assert resolved == "gpu"
    else:
        assert resolved == "cpu"


def test_default_resources_system_unknown_probe(
    default_exec_resources, system_resources, gpu_cpu_probe
):
    resource_caps = ResourceCapabilities(accelerator=["gpu", "cpu"])
    resolved = resolve_accelerator(
        exec_resources=default_exec_resources,
        resource_caps=resource_caps,
        system_resources=system_resources,
        probe_result=gpu_cpu_probe,
        messages={},
    )

    assert resolved == "gpu"


def test_strict_gpu_unavailable(
    gpu_exec_resources_strict, gpu_unavailable_probe, system_resources
):
    resource_caps = ResourceCapabilities(accelerator=["gpu", "cpu"])
    with pytest.raises(
        ValueError,
        match="Requested accelerator 'gpu' is unavailable or unsupported; falling back.",
    ):
        resolve_accelerator(
            exec_resources=gpu_exec_resources_strict,
            resource_caps=resource_caps,
            system_resources=system_resources,
            probe_result=gpu_unavailable_probe,
            messages={},
        )

