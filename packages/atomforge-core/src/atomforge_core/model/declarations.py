"""Declarations that may differ between the variants of a kind.

A manifest's ``supported_properties`` and ``resource_capabilities`` name
either a value, which holds for every spec of the kind, or a function of the
spec, for a kind whose variants differ (a checkpoint published in fp32 only,
a checkpoint without a stress head). A function is a declaration like the
value it returns: deterministic in the spec, host-safe (it must not import
the model's package or inspect the machine), and it should depend on the
variant fields and the local weights, not on settings.

The kind as a whole, for listings, is the union over ``Spec.variants()``.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TypeVar

from atomforge_core.model.spec import ModelSpec
from atomforge_core.property import Property
from atomforge_core.resources.resource_caps import ResourceCapabilities

T = TypeVar("T")

SupportedProperties = frozenset[Property]


def is_per_variant(declaration: object) -> bool:
    """Whether a loaded declaration is a function of the spec rather than a
    value."""
    return callable(declaration) and not isinstance(declaration, type)


def check_supported_properties(value: object) -> SupportedProperties:
    if not isinstance(value, frozenset) or not all(
        isinstance(prop, Property) for prop in value
    ):
        raise TypeError(
            f"supported properties must be a frozenset of Property, got {value!r}"
        )
    return value


def check_resource_capabilities(value: object) -> ResourceCapabilities:
    if not isinstance(value, ResourceCapabilities):
        raise TypeError(
            f"resource capabilities must be a ResourceCapabilities, got {value!r}"
        )
    return value


def resolve_declaration(
    declaration: T | Callable[[ModelSpec], T],
    spec: ModelSpec,
    check: Callable[[object], T],
) -> T:
    """The declaration for one spec: the value itself, or the function's
    result for ``spec``, checked with ``check``."""
    if is_per_variant(declaration):
        return check(declaration(spec))
    return check(declaration)


def union_supported_properties(
    declarations: Iterable[SupportedProperties],
) -> SupportedProperties:
    result: set[Property] = set()
    for declaration in declarations:
        result |= declaration
    return frozenset(result)


def union_resource_capabilities(
    declarations: Iterable[ResourceCapabilities],
) -> ResourceCapabilities:
    """Every accelerator and precision that some declaration has. The
    declarations must agree on which knobs they use."""
    declarations = list(declarations)
    if not declarations:
        raise ValueError("no resource capabilities to combine")
    first = declarations[0]
    uses_accelerator = first.accelerator is not None
    uses_precision = first.precision is not None
    for declaration in declarations[1:]:
        if (declaration.accelerator is not None) != uses_accelerator or (
            declaration.precision is not None
        ) != uses_precision:
            raise ValueError(
                "the variants of a kind must agree on which resource knobs they "
                f"use: {first!r} and {declaration!r}"
            )

    accelerators: list = []
    if uses_accelerator:
        for declaration in declarations:
            accelerators += [
                a for a in declaration.accelerator if a not in accelerators
            ]

    if not uses_precision:
        precision = None
    elif not uses_accelerator:
        precision = []
        for declaration in declarations:
            precision += [p for p in declaration.precision if p not in precision]
        precision = sorted(precision)
    else:
        precision = {}
        for declaration in declarations:
            for accelerator in declaration.accelerator:
                found = precision.setdefault(accelerator, [])
                found += [
                    p for p in declaration.precisions_on(accelerator) if p not in found
                ]
        precision = {a: sorted(p) for a, p in precision.items()}

    return ResourceCapabilities(
        accelerator=accelerators if uses_accelerator else None, precision=precision
    )


def kind_declaration(
    declaration: T | Callable[[ModelSpec], T],
    spec_cls: type[ModelSpec],
    check: Callable[[object], T],
    union: Callable[[Iterable[T]], T],
) -> T:
    """The declaration of the kind as a whole: the value, or the union of the
    function over every generated variant."""
    if not is_per_variant(declaration):
        return check(declaration)
    variants = spec_cls.variants()
    if not variants:
        raise ValueError(
            f"{spec_cls.__name__} generates no variants, so a declaration that "
            "is a function of the spec has no value for the kind"
        )
    return union(check(declaration(variant)) for variant in variants)
