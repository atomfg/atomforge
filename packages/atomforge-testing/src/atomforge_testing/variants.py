"""Which variants of a case's spec the runtime contracts run."""

from __future__ import annotations

import pytest

from atomforge_core.model.spec import ModelSpec


def selected_variant_names(case, config: pytest.Config) -> tuple[str, ...] | None:
    """The variant names the case's runtime contracts run: the case's own
    ``variants``, every generated variant under ``--atomforge-all-variants``,
    or None for the case's spec as it is."""
    if case.variants is not None:
        return tuple(case.variants)
    if not config.getoption("atomforge_all_variants", default=False):
        return None
    try:
        spec_cls = case.manifest.model_spec.load_symbol()
        return tuple(variant.variant_name for variant in spec_cls.variants())
    except Exception:  # noqa: BLE001 - reported by the symbol and spec contracts
        return None


def with_variant(model_spec: ModelSpec, variant_name: str) -> ModelSpec:
    """``model_spec`` with the variant fields of the named variant, keeping
    its settings."""
    if variant_name == model_spec.variant_name:
        return model_spec
    spec_cls = type(model_spec)
    variants = spec_cls.variants()
    for variant in variants:
        if variant.variant_name == variant_name:
            payload = {**model_spec.model_dump(), **variant.variant_payload()}
            return spec_cls.model_validate(payload)
    known = ", ".join(v.variant_name for v in variants)
    raise AssertionError(
        f"the case names variant '{variant_name}', which {model_spec.kind} does "
        f"not generate (its variants: {known})"
    )


def selected_specs(case, config: pytest.Config) -> list[ModelSpec]:
    """The specs the case's runtime contracts run: the case's spec, with the
    variant fields of each selected variant."""
    spec_cls = case.manifest.model_spec.load_symbol()
    spec = case.model_spec_factory(spec_cls)
    names = selected_variant_names(case, config)
    if names is None:
        return [spec]
    return [with_variant(spec, name) for name in names]
