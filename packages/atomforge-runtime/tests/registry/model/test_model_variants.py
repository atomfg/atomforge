"""Acceptance tests for "Variants, settings and local weights in the spec,
design" in the engineering log: the registry returns a spec by variant id,
and the worker checks local weights before loading them."""

from dataclasses import replace
from typing import Annotated, Literal

import pytest

from atomforge_core.model.spec import ModelSpec, Setting, Variant
from atomforge_core.model.weights import LocalWeights
from atomforge_core.protocol.request import InitModelRequest
from atomforge_core.protocol.response import ErrorResponse, InitModelResponse
from atomforge_core.resources.resource_models import ExecutionResources
from atomforge_runtime.backend.subprocess.worker import SubprocessWorker
from atomforge_runtime.registry.model.model_registry import ModelRegistry
from atomforge_runtime.resources import Availability, SystemResources

from runtime_fakes import build_model_registration, build_task_registry


class VariantFakeModel(ModelSpec):
    kind: Literal["fake-model"] = "fake-model"
    model: Annotated[Literal["small", "large"], Variant] = "small"
    scale: Annotated[float, Setting] = 1.0
    weights: LocalWeights | None = None


def _registry() -> ModelRegistry:
    registry = ModelRegistry()
    registration = replace(build_model_registration(), model_spec=VariantFakeModel)
    registry._register(registration, registration.kind)
    return registry


def test_variant_returns_the_spec_for_a_variant_id():
    spec = _registry().variant("fake-model/large")

    assert spec == VariantFakeModel(model="large")


def test_variant_returns_default_settings():
    spec = _registry().variant("fake-model/small")

    assert spec.scale == 1.0
    assert spec.weights is None


@pytest.mark.parametrize("variant_id", ["fake-model/medium", "fake-model"])
def test_variant_rejects_an_unknown_variant(variant_id):
    with pytest.raises(KeyError, match="medium|variant"):
        _registry().variant(variant_id)


def test_variant_rejects_an_unknown_kind():
    with pytest.raises(KeyError, match="snack"):
        _registry().variant("snack/small")


# The worker checks local weights before the executor loads them


def _worker() -> SubprocessWorker:
    return SubprocessWorker(
        stdin=None,
        stdout=None,
        stderr=None,
        name="test_worker",
        task_registry=build_task_registry(),
        model_registry=_registry(),
        system_resources=SystemResources(
            cpu_count=4,
            platform="test_platform",
            architecture="test_architecture",
            hostname="test_hostname",
            gpu_available=Availability.UNAVAILABLE,
        ),
    )


def _init(worker, spec):
    request = InitModelRequest(
        request_id="init",
        model_kind=spec.kind,
        model_payload=spec.model_dump(mode="json"),
        exec_resources=ExecutionResources(),
    )
    response, _ = worker._handle_request(request)
    return response


@pytest.fixture
def weights_file(tmp_path):
    path = tmp_path / "fine-tuned.model"
    path.write_bytes(b"fine-tuned parameters")
    return path


def test_worker_loads_unchanged_local_weights(weights_file):
    spec = VariantFakeModel(weights=LocalWeights(weights_file))

    response = _init(_worker(), spec)

    assert isinstance(response, InitModelResponse)


def test_worker_rejects_local_weights_changed_after_the_spec_was_made(
    weights_file,
):
    spec = VariantFakeModel(weights=LocalWeights(weights_file))
    weights_file.write_bytes(b"overwritten by a later fine-tune")

    response = _init(_worker(), spec)

    assert isinstance(response, ErrorResponse)
    assert "sha256" in f"{response.error} {response.message}"
