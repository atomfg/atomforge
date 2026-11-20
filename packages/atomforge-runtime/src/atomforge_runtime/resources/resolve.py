"""Resolve requested execution resources against a model's capabilities.

Accelerator and precision are resolved together, because a model declares its
precisions per accelerator (torch has no float64 on MPS). The rules:

- Defaults pick the accelerator first (cuda, rocm, mps, cpu: the first the
  model supports and the machine has), then the highest precision it supports.
- ``gpu`` is the first of cuda, rocm and mps that the model supports and the
  machine has.
- An explicit precision is kept in preference to an explicit accelerator: a
  non-strict request for a pair the model does not support changes the
  accelerator, so the numbers are what was asked for and only speed changes.
- A strict request that cannot be honoured raises; a non-strict one records a
  message and falls back.
"""

import os
import platform

from atomforge_core.resources.resource_caps import ResourceCapabilities
from atomforge_core.resources.resource_models import (
    ExecutionResources,
    ResolvedResources,
)
from atomforge_core.resources.resource_probes import ProbeResult
from atomforge_runtime.resources.shared import (
    Accelerator,
    Availability,
    Precision,
    SystemResources,
    handle_resolution_failure,
    handle_unused_knob,
)

# Preference order when the accelerator is left to the resolver, and the
# accelerators that a "gpu" request may resolve to.
DEFAULT_ORDER: tuple[Accelerator, ...] = ("cuda", "rocm", "mps", "cpu")
GPU_ORDER: tuple[Accelerator, ...] = ("cuda", "rocm", "mps")


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

    if resource_caps.accelerator is None:
        accelerator = handle_unused_knob(
            requested=exec_resources.accelerator,
            strict=exec_resources.strict,
            messages=messages,
            key="accelerator",
            message=(
                f"Requested accelerator '{exec_resources.accelerator}' ignored "
                "because the model does not use accelerator selection."
            ),
        )
        precision = _resolve_precision_list(exec_resources, resource_caps, messages)
    else:
        accelerator, precision = _resolve_pair(
            exec_resources, resource_caps, system_resources, probe_result, messages
        )

    return ResolvedResources(
        accelerator=accelerator, precision=precision, messages=messages
    )


def _resolve_precision_list(
    exec_resources: ExecutionResources,
    resource_caps: ResourceCapabilities,
    messages: dict[str, str],
) -> Precision | None:
    """Precision for a model that does not use the accelerator knob."""
    requested = exec_resources.precision
    supported = resource_caps.precisions_on(None)
    if supported is None:
        return _unused_precision(exec_resources, messages)
    if requested == "default":
        return _highest(supported)
    if requested in supported:
        return requested
    handle_resolution_failure(
        strict=exec_resources.strict,
        messages=messages,
        key="precision",
        message=f"Requested precision '{requested}' is unsupported; falling back.",
    )
    return _highest(supported)


def _resolve_pair(
    exec_resources: ExecutionResources,
    caps: ResourceCapabilities,
    system_resources: SystemResources,
    probe_result: ProbeResult | None,
    messages: dict[str, str],
) -> tuple[Accelerator, Precision | None]:
    strict = exec_resources.strict
    declared: list[Accelerator] = list(caps.accelerator or [])
    uses_precision = caps.precision is not None

    def usable(accelerator: Accelerator) -> bool:
        return accelerator in declared and accelerator_available(
            accelerator, system_resources, probe_result
        )

    def supports(accelerator: Accelerator, precision: Precision | None) -> bool:
        if precision is None:
            return True
        return precision in (caps.precisions_on(accelerator) or [])

    # The precision to keep, if one was requested and the model has it.
    wanted: Precision | None = None
    if not uses_precision:
        _unused_precision(exec_resources, messages)
    elif exec_resources.precision != "default":
        requested_precision: Precision = exec_resources.precision
        if any(supports(a, requested_precision) for a in declared):
            wanted = requested_precision
        else:
            handle_resolution_failure(
                strict=strict,
                messages=messages,
                key="precision",
                message=(
                    f"Requested precision '{requested_precision}' is unsupported; "
                    "falling back."
                ),
            )

    def first(order: tuple[Accelerator, ...]) -> Accelerator | None:
        for candidate in order:
            if usable(candidate) and supports(candidate, wanted):
                return candidate
        return None

    requested = exec_resources.accelerator
    accelerator: Accelerator | None
    if requested == "default":
        accelerator = first(DEFAULT_ORDER)
    elif requested == "gpu":
        accelerator = first(GPU_ORDER)
        if accelerator is None:
            handle_resolution_failure(
                strict=strict,
                messages=messages,
                key="accelerator",
                message=(
                    "Requested accelerator 'gpu': no GPU that the model supports "
                    f"{_with(wanted)}is available; falling back."
                ),
            )
            accelerator = first(DEFAULT_ORDER)
    elif usable(requested) and supports(requested, wanted):
        accelerator = requested
    else:
        handle_resolution_failure(
            strict=strict,
            messages=messages,
            key="accelerator",
            message=_failure_message(
                requested, wanted, declared, system_resources, probe_result
            ),
        )
        accelerator = first(DEFAULT_ORDER)

    if accelerator is None:
        raise ValueError("No usable accelerator available.")

    if not uses_precision:
        return accelerator, None
    if wanted is not None:
        return accelerator, wanted
    return accelerator, _highest(caps.precisions_on(accelerator) or [])


def _unused_precision(
    exec_resources: ExecutionResources, messages: dict[str, str]
) -> None:
    return handle_unused_knob(
        requested=exec_resources.precision,
        strict=exec_resources.strict,
        messages=messages,
        key="precision",
        message=(
            f"Requested precision '{exec_resources.precision}' ignored because "
            "the model does not use precision selection."
        ),
    )


def _highest(supported: list[Precision]) -> Precision:
    """The preferred precision: f64 over f32."""
    if "f64" in supported:
        return "f64"
    if "f32" in supported:
        return "f32"
    raise ValueError("No usable precision available.")


def _with(precision: Precision | None) -> str:
    return f"in {precision} " if precision is not None else ""


def _failure_message(
    requested: Accelerator,
    wanted: Precision | None,
    declared: list[Accelerator],
    system_resources: SystemResources,
    probe_result: ProbeResult | None,
) -> str:
    if requested not in declared:
        return (
            f"Requested accelerator '{requested}' is not supported by the model; "
            "falling back."
        )
    if not accelerator_available(requested, system_resources, probe_result):
        if probe_result is not None and requested in probe_result.reasons:
            return probe_result.reasons[requested]
        return f"Requested accelerator '{requested}' is unavailable; falling back."
    return (
        f"The model does not support {wanted} on '{requested}'; keeping {wanted} "
        "and falling back to another accelerator."
    )


def accelerator_available(
    accelerator: Accelerator,
    system_resources: SystemResources,
    probe_result: ProbeResult | None,
) -> bool:
    """Return whether a concrete accelerator appears usable on this worker.

    Without a probe, only CPU, and CUDA when the system reports a GPU, count
    as available: telling ROCm and MPS apart needs the model's framework.
    """
    if accelerator == "cpu":
        return True
    if probe_result is not None:
        return accelerator in probe_result.available_accelerators
    if accelerator == "cuda":
        return system_resources.gpu_available == Availability.AVAILABLE
    return False
