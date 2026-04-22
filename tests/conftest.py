import pytest

from atomforge.structure import Structure
from atomforge.model.ase_lj import LennardJonesExecutor, LennardJones
from atomforge.task.core.resources import ResolvedResources

@pytest.fixture
def example_structure():
    return Structure(
        positions=[[4.5, 0, 0], [5.5, 0, 0]],
        cell=[[10, 0, 0], [0, 10, 0], [0, 0, 10]],
        species=["H", "O"],
        pbc=[False, False, False],
    )

@pytest.fixture
def lj_executor():
    spec = LennardJones()
    resources = ResolvedResources(accelerator="cpu", precision=None, messages=dict())
    return LennardJonesExecutor(spec=spec, resolved_resources=resources)
