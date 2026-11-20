"""Unit tests for the resource translation. They run on the host, without torch, and
cover the GPU mapping that CI cannot execute."""

import pytest

from atomforge_core.resources.resource_models import ResolvedResources

from atomforge_template.definitions import TorchLJResourceCapabilities
from atomforge_template.resources import torch_device, torch_dtype


def resolved(accelerator=None, precision=None):
    return ResolvedResources(accelerator=accelerator, precision=precision)


@pytest.mark.parametrize(
    ("accelerator", "expected"),
    [("cpu", "cpu"), ("cuda", "cuda"), ("mps", "mps"), (None, "cpu")],
)
def test_torch_device(accelerator, expected):
    assert torch_device(resolved(accelerator=accelerator)) == expected


@pytest.mark.parametrize(
    ("precision", "expected"),
    [("f32", "float32"), ("f64", "float64"), (None, "float64")],
)
def test_torch_dtype(precision, expected):
    assert torch_dtype(resolved(precision=precision)) == expected


def test_every_declared_capability_has_a_translation():
    for accelerator, precision in TorchLJResourceCapabilities.pairs():
        torch_device(resolved(accelerator=accelerator))
        torch_dtype(resolved(precision=precision))


def test_undeclared_accelerator_is_rejected():
    with pytest.raises(ValueError, match="rocm"):
        torch_device(resolved(accelerator="rocm"))
