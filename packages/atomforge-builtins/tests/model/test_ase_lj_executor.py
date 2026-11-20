import pytest
from importlib.util import find_spec

from atomforge_core.property import Property


@pytest.mark.skipif(find_spec("ase") is None, reason="Requires ASE installation")
def test_lennard_jones_returns_declared_types(model_executor, example_structure):
    # ModelResult is not validated at runtime: models must return the types it
    # declares (a float, and forces as a list of lists of floats).
    result = model_executor.compute(
        example_structure, frozenset({Property.ENERGY, Property.FORCES})
    )
    assert type(result.energy) is float
    assert type(result.forces) is list
    assert all(type(row) is list for row in result.forces)
    assert all(type(value) is float for row in result.forces for value in row)
