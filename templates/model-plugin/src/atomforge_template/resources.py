"""Translate atomforge's resource names into the ones the model uses.

atomforge describes resources with its own names ("cuda", "mps", "f32", ...).
Each plugin owns the translation to its framework. Rewrite these functions for
yours. ROCm builds of torch call an AMD GPU "cuda", so a model that declares
"rocm" maps it to "cuda" here.

The functions return plain strings, so they can be tested on the host without torch.
"""

from atomforge_core.resources.resource_models import ResolvedResources

_DEVICES = {"cpu": "cpu", "cuda": "cuda", "mps": "mps"}
_DTYPES = {"f32": "float32", "f64": "float64"}


def torch_device(resolved: ResolvedResources) -> str:
    """Name of the torch device, for torch.device(...)."""
    if resolved.accelerator is None:
        return "cpu"
    try:
        return _DEVICES[resolved.accelerator]
    except KeyError:
        raise ValueError(
            f"Unsupported accelerator for torch-lj: {resolved.accelerator!r}"
        ) from None


def torch_dtype(resolved: ResolvedResources) -> str:
    """Name of the torch dtype, for getattr(torch, ...)."""
    if resolved.precision is None:
        return "float64"
    try:
        return _DTYPES[resolved.precision]
    except KeyError:
        raise ValueError(
            f"Unsupported precision for torch-lj: {resolved.precision!r}"
        ) from None
