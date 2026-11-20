"""resolve_resources beyond the acceptance table: unused knobs, precision
lists, and availability without a probe. (Ported from the tests of the former
per-knob resolvers.)"""

import pytest

from atomforge_core.resources.resource_caps import ResourceCapabilities
from atomforge_core.resources.resource_models import ExecutionResources
from atomforge_runtime.resources import (
    Availability,
    SystemResources,
    resolve_resources,
)


def system(gpu=Availability.UNKNOWN) -> SystemResources:
    return SystemResources(
        cpu_count=8,
        platform="Linux",
        architecture="x86_64",
        hostname="test-machine",
        gpu_available=gpu,
    )


def resolve(caps, *, gpu=Availability.UNKNOWN, **request):
    return resolve_resources(
        exec_resources=ExecutionResources(**request),
        resource_caps=caps,
        system_resources=system(gpu),
        probe_result=None,
    )


CPU_CUDA = ResourceCapabilities(
    accelerator=["cpu", "cuda"],
    precision={"cpu": ["f32", "f64"], "cuda": ["f32", "f64"]},
)
PRECISION_ONLY = ResourceCapabilities(precision=["f32", "f64"])


@pytest.mark.parametrize(
    ("gpu", "expected"),
    [
        (Availability.AVAILABLE, "cuda"),
        (Availability.UNKNOWN, "cpu"),
        (Availability.UNAVAILABLE, "cpu"),
    ],
)
def test_without_a_probe_cuda_follows_the_system(gpu, expected):
    assert resolve(CPU_CUDA, gpu=gpu).accelerator == expected


def test_without_a_probe_mps_is_not_assumed():
    caps = ResourceCapabilities(
        accelerator=["cpu", "mps"], precision={"cpu": ["f32"], "mps": ["f32"]}
    )

    assert resolve(caps, gpu=Availability.AVAILABLE).accelerator == "cpu"


def test_unsupported_accelerator_falls_back_with_a_message():
    caps = ResourceCapabilities(accelerator=["cpu"], precision={"cpu": ["f32"]})

    resolved = resolve(caps, accelerator="cuda")

    assert resolved.accelerator == "cpu"
    assert "accelerator" in resolved.messages


def test_unsupported_accelerator_raises_when_strict():
    caps = ResourceCapabilities(accelerator=["cpu"], precision={"cpu": ["f32"]})

    with pytest.raises(ValueError, match="not supported by the model"):
        resolve(caps, accelerator="cuda", strict=True)


def test_precision_list_default_prefers_f64():
    assert resolve(PRECISION_ONLY).precision == "f64"


def test_precision_list_keeps_a_supported_request():
    assert resolve(PRECISION_ONLY, precision="f32").precision == "f32"


def test_precision_list_unsupported_request_falls_back():
    caps = ResourceCapabilities(precision=["f64"])

    resolved = resolve(caps, precision="f32")

    assert resolved.precision == "f64"
    assert "precision" in resolved.messages


def test_precision_list_unsupported_request_raises_when_strict():
    caps = ResourceCapabilities(precision=["f64"])

    with pytest.raises(ValueError):
        resolve(caps, precision="f32", strict=True)


def test_precision_unsupported_everywhere_falls_back_to_the_highest():
    caps = ResourceCapabilities(accelerator=["cpu"], precision={"cpu": ["f64"]})

    resolved = resolve(caps, precision="f32")

    assert (resolved.accelerator, resolved.precision) == ("cpu", "f64")
    assert "precision" in resolved.messages


def test_unused_knobs_resolve_to_none():
    resolved = resolve(ResourceCapabilities())

    assert (resolved.accelerator, resolved.precision) == (None, None)
    assert resolved.messages == {}


def test_explicit_request_for_an_unused_knob_is_noted():
    resolved = resolve(ResourceCapabilities(), accelerator="cuda", precision="f32")

    assert set(resolved.messages) == {"accelerator", "precision"}


def test_explicit_request_for_an_unused_knob_raises_when_strict():
    with pytest.raises(ValueError):
        resolve(ResourceCapabilities(), precision="f32", strict=True)
