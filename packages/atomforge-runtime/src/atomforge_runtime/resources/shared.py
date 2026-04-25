from typing import Literal, TypeAlias
from dataclasses import dataclass
from enum import Enum


Accelerator: TypeAlias = Literal["cpu", "gpu", "mps"]
Precision: TypeAlias = Literal["f32", "f64"]
RequestedAccelerator: TypeAlias = Literal["default", "cpu", "gpu", "mps"]
RequestedPrecision: TypeAlias = Literal["default", "f32", "f64"]
RequestedResource: TypeAlias = RequestedAccelerator | RequestedPrecision


class Availability(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class SystemResources:
    cpu_count: int | None
    platform: str
    architecture: str
    hostname: str | None
    gpu_available: Availability


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
