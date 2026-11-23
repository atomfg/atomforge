"""Supported properties and resource capabilities that differ between the
variants of a kind: a manifest may name a function of the spec instead of a
value."""

from typing import Annotated, Literal

import pytest

from atomforge_core.model.declarations import (
    check_resource_capabilities,
    check_supported_properties,
    is_per_variant,
    kind_declaration,
    resolve_declaration,
    union_resource_capabilities,
    union_supported_properties,
)
from atomforge_core.model.spec import ModelSpec, Setting, Variant
from atomforge_core.property import Property
from atomforge_core.resources.resource_caps import ResourceCapabilities


class TwoFamilies(ModelSpec):
    kind: Literal["two-families"] = "two-families"
    model: Annotated[Literal["small", "large"], Variant] = "small"


BOTH = ResourceCapabilities(
    accelerator=["cpu", "cuda"],
    precision={"cpu": ["f32", "f64"], "cuda": ["f32", "f64"]},
)
F32 = ResourceCapabilities(
    accelerator=["cpu", "cuda"], precision={"cpu": ["f32"], "cuda": ["f32"]}
)


def capabilities(spec: TwoFamilies) -> ResourceCapabilities:
    return BOTH if spec.model == "small" else F32


def properties(spec: TwoFamilies) -> frozenset[Property]:
    if spec.model == "small":
        return frozenset({Property.ENERGY, Property.FORCES, Property.STRESS})
    return frozenset({Property.ENERGY, Property.FORCES})


def test_a_value_is_not_per_variant_and_a_function_is():
    assert not is_per_variant(BOTH)
    assert not is_per_variant(frozenset({Property.ENERGY}))
    assert is_per_variant(capabilities)


def test_a_value_holds_for_every_spec():
    assert (
        resolve_declaration(
            BOTH, TwoFamilies(model="large"), check_resource_capabilities
        )
        is BOTH
    )


def test_a_function_is_resolved_for_the_spec():
    large = TwoFamilies(model="large")
    assert resolve_declaration(capabilities, large, check_resource_capabilities) == F32
    assert resolve_declaration(properties, large, check_supported_properties) == {
        Property.ENERGY,
        Property.FORCES,
    }


def test_a_function_that_returns_the_wrong_type_is_rejected():
    with pytest.raises(TypeError, match="ResourceCapabilities"):
        resolve_declaration(
            lambda spec: {"cpu": ["f32"]}, TwoFamilies(), check_resource_capabilities
        )
    with pytest.raises(TypeError, match="frozenset of Property"):
        resolve_declaration(
            lambda spec: {"energy"}, TwoFamilies(), check_supported_properties
        )


def test_the_kind_is_the_union_over_its_variants():
    assert (
        kind_declaration(
            capabilities,
            TwoFamilies,
            check_resource_capabilities,
            union_resource_capabilities,
        )
        == BOTH
    )
    assert kind_declaration(
        properties, TwoFamilies, check_supported_properties, union_supported_properties
    ) == {Property.ENERGY, Property.FORCES, Property.STRESS}


def test_union_keeps_accelerators_that_only_some_variants_have():
    cpu_only = ResourceCapabilities(accelerator=["cpu"], precision={"cpu": ["f64"]})
    mps = ResourceCapabilities(
        accelerator=["cpu", "mps"], precision={"cpu": ["f32"], "mps": ["f32"]}
    )

    union = union_resource_capabilities([cpu_only, mps])

    assert union.accelerator == ["cpu", "mps"]
    assert union.precision == {"cpu": ["f32", "f64"], "mps": ["f32"]}


def test_union_of_precision_lists_and_of_unused_knobs():
    assert union_resource_capabilities(
        [
            ResourceCapabilities(precision=["f64"]),
            ResourceCapabilities(precision=["f32"]),
        ]
    ) == ResourceCapabilities(precision=["f32", "f64"])
    assert (
        union_resource_capabilities([ResourceCapabilities(), ResourceCapabilities()])
        == ResourceCapabilities()
    )


def test_variants_must_agree_on_the_knobs_they_use():
    with pytest.raises(ValueError, match="agree"):
        union_resource_capabilities(
            [ResourceCapabilities(precision=["f32"]), ResourceCapabilities()]
        )


def test_a_function_needs_variants_for_the_kind():
    class NoDefault(ModelSpec):
        kind: Literal["no-default"] = "no-default"
        model: Annotated[Literal["a"], Variant] = "a"
        scale: Annotated[float, Setting]  # required, so no spec has defaults

    with pytest.raises(ValueError, match="no variants"):
        kind_declaration(
            lambda spec: BOTH,
            NoDefault,
            check_resource_capabilities,
            union_resource_capabilities,
        )
