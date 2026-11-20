"""Acceptance tests for accelerators named by backend and precision declared
per accelerator (engineering log: "Accelerators by backend, and precision per
accelerator, design")."""

import pytest
from pydantic import ValidationError

from atomforge_core.resources.resource_caps import ResourceCapabilities
from atomforge_core.resources.resource_models import (
    ExecutionResources,
    ResolvedResources,
)
from atomforge_core.resources.resource_probes import ProbeResult

BACKENDS = ["cpu", "cuda", "rocm", "mps"]


# Declaring capabilities


def test_precision_mapping_with_the_accelerators_as_keys_is_accepted():
    caps = ResourceCapabilities(
        accelerator=["cpu", "cuda", "mps"],
        precision={"cpu": ["f32", "f64"], "cuda": ["f32", "f64"], "mps": ["f32"]},
    )

    assert caps.precision["mps"] == ["f32"]


@pytest.mark.parametrize(
    "precision",
    [
        {"cpu": ["f32", "f64"]},  # an accelerator without precisions
        {"cpu": ["f32"], "cuda": ["f32"], "mps": ["f32"]},  # a key not declared
    ],
    ids=["missing-key", "extra-key"],
)
def test_precision_mapping_keys_must_equal_the_accelerators(precision):
    with pytest.raises(ValidationError):
        ResourceCapabilities(accelerator=["cpu", "cuda"], precision=precision)


def test_an_accelerator_without_precisions_is_rejected():
    with pytest.raises(ValidationError):
        ResourceCapabilities(accelerator=["cpu"], precision={"cpu": []})


def test_a_precision_list_is_rejected_when_accelerators_are_declared():
    with pytest.raises(ValidationError):
        ResourceCapabilities(accelerator=["cpu", "cuda"], precision=["f32", "f64"])


def test_a_precision_list_is_accepted_without_accelerators():
    caps = ResourceCapabilities(accelerator=None, precision=["f32", "f64"])

    assert caps.precision == ["f32", "f64"]


def test_a_precision_mapping_is_rejected_without_accelerators():
    with pytest.raises(ValidationError):
        ResourceCapabilities(accelerator=None, precision={"cpu": ["f32"]})


def test_accelerators_without_precision_are_accepted():
    caps = ResourceCapabilities(accelerator=["cpu", "mps"], precision=None)

    assert caps.precision is None


def test_neither_knob_is_accepted():
    caps = ResourceCapabilities()

    assert caps.accelerator is None and caps.precision is None


@pytest.mark.parametrize("accelerator", BACKENDS)
def test_capabilities_accept_every_backend(accelerator):
    ResourceCapabilities(accelerator=[accelerator], precision={accelerator: ["f32"]})


def test_capabilities_reject_gpu():
    with pytest.raises(ValidationError):
        ResourceCapabilities(accelerator=["cpu", "gpu"], precision=None)


# Requesting and resolving


@pytest.mark.parametrize("accelerator", ["default", "gpu", *BACKENDS])
def test_requests_accept_gpu_default_and_every_backend(accelerator):
    assert ExecutionResources(accelerator=accelerator).accelerator == accelerator


@pytest.mark.parametrize("accelerator", BACKENDS)
def test_resolved_resources_accept_every_backend(accelerator):
    resolved = ResolvedResources(accelerator=accelerator, precision="f32")

    assert resolved.accelerator == accelerator


@pytest.mark.parametrize("accelerator", ["gpu", "default"])
def test_resolved_resources_reject_request_only_names(accelerator):
    with pytest.raises(ValidationError):
        ResolvedResources(accelerator=accelerator, precision="f32")


def test_probe_results_name_backends():
    probe = ProbeResult(available_accelerators=frozenset({"cpu", "rocm"}))

    assert probe.available_accelerators == {"cpu", "rocm"}


def test_probe_results_reject_gpu():
    with pytest.raises(ValidationError):
        ProbeResult(available_accelerators=frozenset({"cpu", "gpu"}))
