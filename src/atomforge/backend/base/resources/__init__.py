from dataclasses import dataclass
from enum import Enum
import os
import platform

from atomforge.model.base.resource_caps import ResourceCapabilities
from atomforge.model.probes import ProbeResult
from atomforge.task.base.resources import ExecutionResources, ResolvedResources


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


from .accelerator import resolve_accelerator
from .precision import resolve_precision


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


__all__ = [
    "Availability",
    "SystemResources",
    "discover_system_resources",
    "resolve_resources",
]
