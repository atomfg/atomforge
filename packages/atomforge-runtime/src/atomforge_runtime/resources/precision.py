from atomforge_core.resources.resource_caps import ResourceCapabilities
from atomforge_core.resources.resource_models import ExecutionResources
from atomforge_runtime.resources.shared import (
    Precision,
    RequestedPrecision,
    handle_resolution_failure,
    handle_unused_knob,
)


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


def normalize_precision_capabilities(
    supported: list[Precision],
) -> list[Precision]:
    """Validate and return the model-supported precision list."""
    if len(supported) == 0:
        raise ValueError("Model precision capability list is empty.")
    return list(supported)


def default_precision(supported: list[Precision]) -> Precision:
    """Choose the preferred supported precision, preferring f64 over f32."""
    if "f64" in supported:
        return "f64"
    if "f32" in supported:
        return "f32"
    raise ValueError("No usable precision available.")
