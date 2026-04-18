import pytest

from atomforge.structure import Structure
from atomforge.model.ase_lj import LennardJonesExecutor, LennardJones
from atomforge.task.base.resources import ResolvedResources

@pytest.fixture
def example_structure():
    return Structure(
        positions=[[0, 0, 0], [1, 1, 1]],
        cell=[[2, 0, 0], [0, 2, 0], [0, 0, 2]],
        species=["H", "O"],
        pbc=[True, True, True],
    )

@pytest.fixture
def lj_executor():
    spec = LennardJones()
    resources = ResolvedResources(accelerator="cpu", precision=None, messages=dict())
    return LennardJonesExecutor(spec=spec, resolved_resources=resources)