from atomforge.task.base.resources import ExecutionResources, ResolvedResources
from atomforge.backend.base.resources import (
    Availability,
    resolve_accelerator,
    SystemResources,
)
from atomforge.model.base.resource_caps import ResourceCapabilities
from atomforge.model.probes import ProbeResult

import pytest


@pytest.fixture()
def default_exec_resources() -> ExecutionResources:
    return ExecutionResources(
        strict=False,
    )


@pytest.fixture()
def gpu_exec_resources() -> ExecutionResources:
    return ExecutionResources(
        accelerator="gpu",
        strict=False,
    )


@pytest.fixture()
def gpu_exec_resources_strict() -> ExecutionResources:
    return ExecutionResources(
        accelerator="gpu",
        strict=True,
    )


@pytest.fixture()
def gpu_cpu_probe() -> ProbeResult:
    return ProbeResult(available_accelerators=["gpu", "cpu"])


@pytest.fixture()
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
    """
    If the model is incapable it will always downgrade to CPU, even if GPU is available.
    """
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
    """
    Test that a probe result always overrides system GPU availability, even if it is unknown or unavailable.
    With probe result that GPU is available, it should be chosen.
    """
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
    """
    Test that if no accelerator is requested, the best available accelerator is chosen.
    """
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
    """
    Test that if no accelerator is requested, the best available accelerator is chosen.
    With probe result that GPU is available, it should be chosen even if system GPU availability is unknown.
    """
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
    """
    Test that if GPU is requested in strict mode but is unavailable according to the probe, an error is raised.
    """
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
