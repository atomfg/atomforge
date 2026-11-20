"""What a model declares, turned into test parameters, and the checks that a
result has the declared properties in the right shape.

The pytest plugin parametrizes contract tests with these: a test that takes
``atomforge_declared_property`` runs once per declared property, and so on.
Parameters are built at collection from the case's manifest. If a manifest
symbol cannot be loaded, the parametrized tests are skipped with the error as
the reason; the symbol contracts report the failure itself.
"""

from __future__ import annotations

from collections.abc import Callable
import math
from numbers import Real
from typing import Literal, get_args, get_origin

import pytest

from atomforge_core.property import Property
from atomforge_core.resources.resource_models import ExecutionResources
from atomforge_core.structure import StructureData

# Accelerators that need hardware a test machine may not have, and the
# marker (enabled by the matching option) that gates them.
ACCELERATOR_MARKERS = {
    "cuda": pytest.mark.atomforge_cuda,
    "rocm": pytest.mark.atomforge_rocm,
    "mps": pytest.mark.atomforge_mps,
}


def _unloadable(what: str, exc: Exception):
    return [
        pytest.param(
            None,
            id="unloadable",
            marks=pytest.mark.skip(reason=f"could not load {what}: {exc!r}"),
        )
    ]


def declared_property_params(case) -> list:
    try:
        supported = case.manifest.supported_properties.load_symbol()
    except Exception as exc:  # noqa: BLE001 - reported by the symbol contract
        return _unloadable("supported properties", exc)
    return [pytest.param(prop, id=prop.value) for prop in Property if prop in supported]


def declared_resources_params(case) -> list:
    try:
        capabilities = case.manifest.resource_capabilities.load_symbol()
    except Exception as exc:  # noqa: BLE001 - reported by the symbol contract
        return _unloadable("resource capabilities", exc)
    # Only the declared pairs: a model may support a precision on some
    # accelerators only. A knob the model does not use runs as "default".
    params = []
    for accelerator, precision in capabilities.pairs():
        accelerator = accelerator or "default"
        precision = precision or "default"
        marker = ACCELERATOR_MARKERS.get(accelerator)
        params.append(
            pytest.param(
                ExecutionResources(
                    accelerator=accelerator, precision=precision, strict=True
                ),
                id=f"{accelerator}-{precision}",
                marks=[marker] if marker is not None else [],
            )
        )
    return params


def environment_profiles(spec_cls) -> tuple[str, ...]:
    """The values a spec's ``environment_profile`` field allows: the members of
    its ``Literal`` type, or only ``"tested"`` if it is not a ``Literal``."""
    field = spec_cls.model_fields.get("environment_profile")
    if field is not None and get_origin(field.annotation) is Literal:
        return tuple(get_args(field.annotation))
    return ("tested",)


def environment_profile_params(case) -> list:
    try:
        spec_cls = case.manifest.model_spec.load_symbol()
    except Exception as exc:  # noqa: BLE001 - reported by the symbol contract
        return _unloadable("the model spec", exc)
    return [
        pytest.param(profile, id=profile) for profile in environment_profiles(spec_cls)
    ]


def result_request_params(case) -> list:
    """Each declared property on its own and all declared properties
    together (id ``all``), since executors can branch on what is
    requested."""
    try:
        supported = case.manifest.supported_properties.load_symbol()
    except Exception as exc:  # noqa: BLE001 - reported by the symbol contract
        return _unloadable("supported properties", exc)
    declared = [prop for prop in Property if prop in supported]
    return [pytest.param(frozenset({prop}), id=prop.value) for prop in declared] + [
        pytest.param(frozenset(declared), id="all")
    ]


# In this order, so that the profile comes first in a test id
# (``[latest-stress]``).
PARAMETRIZATIONS: dict[str, Callable] = {
    "atomforge_environment_profile": environment_profile_params,
    "atomforge_declared_property": declared_property_params,
    "atomforge_declared_resources": declared_resources_params,
    "atomforge_result_request": result_request_params,
}


# Result checks


def _is_finite_number(value) -> bool:
    return isinstance(value, Real) and math.isfinite(value)


def assert_energy_result(result) -> None:
    assert result.energy is not None, "energy was declared but not returned"
    assert _is_finite_number(result.energy), (
        f"energy must be a finite number, got {result.energy!r}"
    )


def _assert_rows(name: str, rows, n_rows: int, n_columns: int) -> None:
    assert rows is not None, f"{name} was declared but not returned"
    assert isinstance(rows, list), f"{name} must be a list, got {type(rows)}"
    assert len(rows) == n_rows, f"{name} must have {n_rows} rows, got {len(rows)}"
    for row in rows:
        assert isinstance(row, list) and len(row) == n_columns, (
            f"each row of {name} must be a list of {n_columns} numbers, got {row!r}"
        )
        assert all(_is_finite_number(value) for value in row), (
            f"{name} must contain finite numbers, got {row!r}"
        )


def assert_forces_result(result, structure: StructureData) -> None:
    _assert_rows("forces", result.forces, len(structure.numbers), 3)


def assert_stress_result(result, structure: StructureData) -> None:
    _assert_rows("stress", result.stress, 3, 3)


def _assert_per_atom(name: str, values, structure: StructureData) -> None:
    n_atoms = len(structure.numbers)
    assert values is not None, f"{name} was declared but not returned"
    assert isinstance(values, list), f"{name} must be a list, got {type(values)}"
    assert len(values) == n_atoms, (
        f"{name} must have one value per atom ({n_atoms}), got {len(values)}"
    )
    assert all(_is_finite_number(value) for value in values), (
        f"{name} must contain finite numbers, got {values!r}"
    )


def assert_energies_result(result, structure: StructureData) -> None:
    _assert_per_atom("energies", result.energies, structure)


def assert_magmoms_result(result, structure: StructureData) -> None:
    _assert_per_atom("magmoms", result.magmoms, structure)


PROPERTY_CHECKS: dict[Property, Callable] = {
    Property.ENERGY: lambda result, structure: assert_energy_result(result),
    Property.FORCES: assert_forces_result,
    Property.STRESS: assert_stress_result,
    Property.ENERGIES: assert_energies_result,
    Property.MAGMOMS: assert_magmoms_result,
}
