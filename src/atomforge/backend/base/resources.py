from dataclasses import dataclass
from enum import Enum
import os
import platform
from typing import Literal, TypeAlias

from atomforge.model.base.resource_caps import ResourceCapabilities
from atomforge.model.probes import ProbeResult
from atomforge.task.base.resources import ExecutionResources, ResolvedResources

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


def discover_system_resources() -> SystemResources:
    """Return basic worker-local system facts using only the standard library."""
    return SystemResources(
        cpu_count=os.cpu_count(),
        platform=platform.system(),
        architecture=platform.machine(),
        hostname=platform.node() or None,
        gpu_available=Availability.UNKNOWN,
    )


def resolve_resources(
    exec_resources: ExecutionResources,
    resource_caps: ResourceCapabilities,
    system_resources: SystemResources,
    probe_result: ProbeResult | None = None,
) -> ResolvedResources:
    """Resolve requested resources into concrete settings or None for unused knobs."""
    messages: dict[str, str] = {}

    accelerator = resolve_accelerator(
        exec_resources=exec_resources,
        resource_caps=resource_caps,
        system_resources=system_resources,
        probe_result=probe_result,
        messages=messages,
    )

    precision = resolve_precision(
        exec_resources=exec_resources,
        resource_caps=resource_caps,
        messages=messages,
    )

    return ResolvedResources(
        accelerator=accelerator,
        precision=precision,
        messages=messages,
    )


def resolve_accelerator(
    exec_resources: ExecutionResources,
    resource_caps: ResourceCapabilities,
    system_resources: SystemResources,
    probe_result: ProbeResult | None,
    messages: dict[str, str],
) -> Accelerator | None:
    """Resolve accelerator choice, or None if the model does not use accelerator selection."""
    supported = resource_caps.accelerator
    requested: RequestedAccelerator = exec_resources.accelerator

    if supported is None:
        return handle_unused_knob(
            requested=requested,
            strict=exec_resources.strict,
            messages=messages,
            key="accelerator",
            message=f"Requested accelerator '{requested}' ignored because the model does not use accelerator selection.",
        )

    normalized = normalize_accelerator_capabilities(supported)

    if requested == "default":
        return default_accelerator(normalized, system_resources, probe_result)

    concrete_requested: Accelerator = requested
    if concrete_requested in normalized and accelerator_available(
        concrete_requested, system_resources, probe_result
    ):
        return concrete_requested

    handle_resolution_failure(
        strict=exec_resources.strict,
        messages=messages,
        key="accelerator",
        message=accelerator_failure_message(concrete_requested, probe_result),
    )
    return fallback_accelerator(normalized, system_resources, probe_result)


def resolve_precision(
    exec_resources: ExecutionResources,
    resource_caps: ResourceCapabilities,
    messages: dict[str, str],
) -> Precision | None:
    """Resolve precision choice, or None if the model does not use precision selection."""
    supported = resource_caps.precision
    requested: RequestedPrecision = exec_resources.precision

    if supported is None:
        return handle_unused_knob(
            requested=requested,
            strict=exec_resources.strict,
            messages=messages,
            key="precision",
            message=f"Requested precision '{requested}' ignored because the model does not use precision selection.",
        )

    normalized = normalize_precision_capabilities(supported)

    if requested == "default":
        return default_precision(normalized)

    concrete_requested: Precision = requested
    if concrete_requested in normalized:
        return concrete_requested

    handle_resolution_failure(
        strict=exec_resources.strict,
        messages=messages,
        key="precision",
        message=f"Requested precision '{concrete_requested}' is unsupported; falling back.",
    )
    return default_precision(normalized)


def normalize_accelerator_capabilities(
    supported: list[Accelerator],
) -> list[Accelerator]:
    """Validate and return the model-supported accelerator list."""
    if len(supported) == 0:
        raise ValueError("Model accelerator capability list is empty.")
    return list(supported)


def normalize_precision_capabilities(
    supported: list[Precision],
) -> list[Precision]:
    """Validate and return the model-supported precision list."""
    if len(supported) == 0:
        raise ValueError("Model precision capability list is empty.")
    return list(supported)


def default_accelerator(
    supported: list[Accelerator],
    system_resources: SystemResources,
    probe_result: ProbeResult | None,
) -> Accelerator:
    """Choose the preferred supported accelerator in GPU, then MPS, then CPU order."""
    for candidate in ("gpu", "mps", "cpu"):
        if candidate in supported and accelerator_available(
            candidate, system_resources, probe_result
        ):
            return candidate
    raise ValueError("No usable accelerator available.")


def fallback_accelerator(
    supported: list[Accelerator],
    system_resources: SystemResources,
    probe_result: ProbeResult | None,
) -> Accelerator:
    """Choose a supported fallback accelerator after a specific request cannot be honored."""
    return default_accelerator(supported, system_resources, probe_result)


def default_precision(supported: list[Precision]) -> Precision:
    """Choose the preferred supported precision, preferring f64 over f32."""
    if "f64" in supported:
        return "f64"
    if "f32" in supported:
        return "f32"
    raise ValueError("No usable precision available.")


def accelerator_available(
    accelerator: Accelerator,
    system_resources: SystemResources,
    probe_result: ProbeResult | None,
) -> bool:
    """Return whether a concrete accelerator appears usable on this worker."""
    if accelerator == "cpu":
        return True

    if probe_result is not None:
        return accelerator in probe_result.available_accelerators

    if accelerator == "gpu":
        return system_resources.gpu_available == Availability.AVAILABLE

    if accelerator == "mps":
        return False

    raise ValueError(f"Unknown accelerator: {accelerator}")


def accelerator_failure_message(
    requested: Accelerator,
    probe_result: ProbeResult | None,
) -> str:
    """Build the message used when a concrete accelerator request cannot be honored."""
    if probe_result is not None and requested in probe_result.reasons:
        return probe_result.reasons[requested]
    return f"Requested accelerator '{requested}' is unavailable or unsupported; falling back."


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
