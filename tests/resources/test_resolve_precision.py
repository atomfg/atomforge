import pytest

from atomforge._runtime.resources.precision import resolve_precision
from atomforge._core.resources.resource_models import ExecutionResources
from atomforge._core.resources.resource_caps import ResourceCapabilities

def test_resolve_precision_default_prefer_f64():
    exec_resources = ExecutionResources()
    resource_caps = ResourceCapabilities(precision=["f32", "f64"])
    resolved = resolve_precision(exec_resources, resource_caps, messages={})
    assert resolved == "f64"

def test_resolve_precision_default_fallback():
    exec_resources = ExecutionResources()
    resource_caps = ResourceCapabilities(precision=["f32"])
    resolved = resolve_precision(exec_resources, resource_caps, messages={})
    assert resolved == "f32"

def test_resolve_precision_specified():
    exec_resources = ExecutionResources(precision="f32")
    resource_caps = ResourceCapabilities(precision=["f32", "f64"])
    resolved = resolve_precision(exec_resources, resource_caps, messages={})
    assert resolved == "f32"

def test_resolve_precision_unsupported():
    exec_resources = ExecutionResources(precision="f32")
    resource_caps = ResourceCapabilities(precision=["f64"])
    resolved = resolve_precision(exec_resources, resource_caps, messages={})
    assert resolved == "f64"  # Falls back to default if specified precision is unsupported

def test_resolve_precision_unsupported_strict():
    exec_resources = ExecutionResources(precision="f32", strict=True)
    resource_caps = ResourceCapabilities(precision=["f64"])

    with pytest.raises(ValueError):
        resolve_precision(exec_resources, resource_caps, messages={})

