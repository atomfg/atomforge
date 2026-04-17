from typing import Literal, TypeAlias


Accelerator: TypeAlias = Literal["cpu", "gpu", "mps"]
Precision: TypeAlias = Literal["f32", "f64"]
RequestedAccelerator: TypeAlias = Literal["default", "cpu", "gpu", "mps"]
RequestedPrecision: TypeAlias = Literal["default", "f32", "f64"]
RequestedResource: TypeAlias = RequestedAccelerator | RequestedPrecision


def handle_unused_knob(
    requested: RequestedResource,
    strict: bool,
    messages: dict[str, str],
    key: str,
    message: str,
) -> None:
    """Return None for an unused knob, raising only for explicit strict requests."""
    if requested == "default":
        return None
    if strict:
        raise ValueError(message)
    messages[key] = message
    return None


def handle_resolution_failure(
    strict: bool,
    messages: dict[str, str],
    key: str,
    message: str,
) -> None:
    """Record a downgrade message or raise immediately when strict mode is enabled."""
    if strict:
        raise ValueError(message)
    messages[key] = message
