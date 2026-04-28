import pytest

from atomforge_core.resources.resource_models import ResolvedResources
from atomforge_core.structure import StructureData


@pytest.fixture
def example_structure():
    return StructureData(
        positions=[[4.5, 0, 0], [5.5, 0, 0]],
        cell=[[10, 0, 0], [0, 10, 0], [0, 0, 10]],
        numbers=[1, 8],
        pbc=[False, False, False],
    )


@pytest.fixture
def model_executor():
    from atomforge_builtins.model.ase_lj import LennardJones, LennardJonesExecutor

    resources = ResolvedResources(accelerator="cpu", precision=None, messages={})
    model = LennardJones(sigma=0.5, epsilon=2)
    return LennardJonesExecutor(model, resources)

