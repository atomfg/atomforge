"""Reference values for `ModelReferenceContract`: what is stored, how it is
compared, and under which conditions it is recorded.

Needs the ``regression`` extra (numpy and pytest-regressions); it is imported
only by the reference tests, so the other contracts do without it.
"""

from __future__ import annotations

import pytest

from atomforge_core.resources.resource_caps import ResourceCapabilities
from atomforge_core.resources.resource_models import ExecutionResources

from atomforge_testing.physics import ReferenceTolerances

EXTRA_MESSAGE = (
    "the reference contract needs pytest-regressions and numpy: add "
    "atomforge-testing[regression] to the plugin's test dependencies"
)

# The profile whose test records references; every profile compares with them.
RECORDING_PROFILE = "tested"


def ndarrays_regression(request: pytest.FixtureRequest):
    """pytest-regressions' fixture, or a failure naming the extra."""
    try:
        import numpy  # noqa: F401

        return request.getfixturevalue("ndarrays_regression")
    except (ImportError, pytest.FixtureLookupError):
        pytest.fail(EXTRA_MESSAGE, pytrace=False)


def reference_name(kind: str, variant_name: str, structure_name: str) -> str:
    return f"{kind}-{variant_name}-{structure_name}"


def recording_resources(capabilities: ResourceCapabilities) -> ExecutionResources:
    """CPU, at the highest precision the model supports there. A knob the model
    does not use (``None``) is left at ``default``."""
    accelerators = capabilities.accelerator
    if accelerators is None:
        accelerator = None
    elif "cpu" in accelerators:
        accelerator = "cpu"
    else:
        accelerator = accelerators[0]
    precisions = capabilities.precisions_on(accelerator)
    if precisions is None:
        precision = "default"
    elif "f64" in precisions:
        precision = "f64"
    else:
        precision = precisions[0]
    return ExecutionResources(accelerator=accelerator or "default", precision=precision)


def arrays(result, n_atoms: int) -> dict:
    """The stored arrays: energy per atom, and forces and stress when present."""
    import numpy as np

    data = {"energy_per_atom": np.asarray([result.energy / n_atoms], dtype=float)}
    if result.forces is not None:
        data["forces"] = np.asarray(result.forces, dtype=float)
    if result.stress is not None:
        data["stress"] = np.asarray(result.stress, dtype=float)
    return data


def tolerances(reference_tolerances: ReferenceTolerances) -> dict:
    """Absolute tolerances per array for ``ndarrays_regression``. ``rtol`` is
    passed as zero: otherwise numpy's ``isclose`` default applies."""
    return {
        field: {"atol": getattr(reference_tolerances, field), "rtol": 0.0}
        for field in ("energy_per_atom", "forces", "stress")
    }
