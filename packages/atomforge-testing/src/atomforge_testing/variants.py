"""Which variants of a case's spec the runtime contracts run."""

from __future__ import annotations

import pytest


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
