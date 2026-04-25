import os
import platform


from atomforge_runtime.resources.shared import SystemResources, Availability
from atomforge_core.resources.resource_caps import ResourceCapabilities
from atomforge_core.resources.resource_probes import ProbeResult
from atomforge_core.resources.resource_models import ExecutionResources, ResolvedResources


from atomforge_runtime.resources.accelerator import resolve_accelerator
from atomforge_runtime.resources.precision import resolve_precision


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
