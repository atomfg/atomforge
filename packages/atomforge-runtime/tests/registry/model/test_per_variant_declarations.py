"""A manifest's supported properties and resource capabilities may be
functions of the spec, when the variants of a kind differ."""

import pytest

from atomforge_core.property import Property
from atomforge_core.resources.resource_models import ExecutionResources
from atomforge_runtime.resources import (
    Availability,
    SystemResources,
    resolve_resources,
)
from atomforge_runtime.task.host_checks import check_required_properties
from runtime_fakes import FakeFamily, FakeTask, build_family_registration


def test_a_variant_gets_its_own_declarations():
    registration = build_family_registration()
    large = FakeFamily(model="large")

    assert registration.load_supported_properties(large) == {Property.ENERGY}
    assert registration.load_resource_capabilities(large).precisions_on("cpu") == [
        "f32"
    ]


def test_without_a_spec_the_kind_is_the_union_of_its_variants():
    registration = build_family_registration()

    assert registration.load_supported_properties() == {
        Property.ENERGY,
        Property.FORCES,
    }
    assert registration.load_resource_capabilities().precisions_on("cpu") == [
        "f32",
        "f64",
    ]


def test_strict_validation_loads_a_function():
    build_family_registration().validate_strict()


def test_a_function_returning_the_wrong_type_names_the_variant():
    registration = build_family_registration(
        resource_capabilities="runtime_fakes:fake_family_wrong_type"
    )

    with pytest.raises(TypeError, match="fake-family/large"):
        registration.load_resource_capabilities(FakeFamily(model="large"))


def test_a_function_that_raises_a_validation_error_keeps_its_message():
    registration = build_family_registration(
        resource_capabilities="runtime_fakes:fake_family_invalid_capabilities"
    )

    with pytest.raises(ValueError, match="(?s)fake-family/small.*precision keys"):
        registration.load_resource_capabilities(FakeFamily())


def test_the_kind_union_is_computed_once(monkeypatch):
    registration = build_family_registration()
    first = registration.load_resource_capabilities()
    monkeypatch.setattr(
        FakeFamily, "variants", classmethod(lambda cls: pytest.fail("recomputed"))
    )

    assert registration.load_resource_capabilities() == first


def test_the_host_check_uses_the_variant(example_structure):
    registration = build_family_registration()
    task = FakeTask(structure=example_structure)  # requires energy and forces

    assert check_required_properties(task, registration, FakeFamily()).ok
    report = check_required_properties(task, registration, FakeFamily(model="large"))
    assert not report.ok
    assert "fake-family/large" in report.reason


def test_resolution_falls_back_to_the_variants_own_precision():
    caps = build_family_registration().load_resource_capabilities(
        FakeFamily(model="large")
    )
    system = SystemResources(
        cpu_count=1,
        platform="Linux",
        architecture="x86_64",
        hostname="test",
        gpu_available=Availability.UNAVAILABLE,
    )

    default = resolve_resources(
        exec_resources=ExecutionResources(),
        resource_caps=caps,
        system_resources=system,
        probe_result=None,
    )
    assert default.precision == "f32"

    with pytest.raises(Exception, match="f64"):
        resolve_resources(
            exec_resources=ExecutionResources(precision="f64", strict=True),
            resource_caps=caps,
            system_resources=system,
            probe_result=None,
        )
