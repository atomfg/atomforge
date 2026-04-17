from atomforge.model.base.resource_caps import ResourceCapabilities
from atomforge.model.probes import ProbeResult
from atomforge.task.base.resources import ExecutionResources

from . import Availability, SystemResources
from .shared import (
    Accelerator,
    RequestedAccelerator,
    handle_resolution_failure,
    handle_unused_knob,
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


def normalize_accelerator_capabilities(
    supported: list[Accelerator],
) -> list[Accelerator]:
    """Validate and return the model-supported accelerator list."""
    if len(supported) == 0:
        raise ValueError("Model accelerator capability list is empty.")
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
