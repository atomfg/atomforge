import pytest
from importlib.util import find_spec

import numpy as np

from atomforge_core.property import Property

pytestmark = pytest.mark.skipif(
    find_spec("ase") is None, reason="Requires ASE installation"
)


@pytest.fixture
def lj_result(model_executor, example_structure):
    # ModelResult is not validated at runtime: models must return the types it
    # declares ("Model results as float64 arrays, design").
    return model_executor.compute(
        example_structure, frozenset({Property.ENERGY, Property.FORCES})
    )


def test_lennard_jones_energy_is_a_float(lj_result):
    assert type(lj_result.energy) is float


def test_lennard_jones_forces_are_a_float64_array(lj_result, example_structure):
    forces = lj_result.forces
    assert (type(forces), forces.dtype, forces.shape) == (
        np.ndarray,
        np.float64,
        (len(example_structure.numbers), 3),
    )
