import pytest
from ase import Atoms

from atomforge.model.ase_lj import LennardJones
from atomforge.task.singlepoint import SinglePoint

@pytest.fixture(scope="module", params=[["forces", "energy"], ["forces"], ["energy"]])
def properties(request):
    return request.param

@pytest.fixture(scope="module")
def single_point_task(properties):

    atoms = Atoms(
        "HOH", positions=[[0, 0, 0], [0, 0, 1], [1, 0, 0]], cell=[10, 10, 10], pbc=False
    )

    task = SinglePoint(structure=atoms, properties=properties)

    return task

@pytest.fixture(scope="module")
def single_point_result(backend, single_point_task):
    from atomforge.task.core.resources import ExecutionResources

    resources = ExecutionResources(accelerator="cpu", precision="f64")
    model = LennardJones()

    result = backend.execute(single_point_task, model, resources)

    return result


def test_result_kind(single_point_result):
    assert single_point_result.kind == "single_point"


def test_result_forces(single_point_result, properties):
    if "forces" in properties:
        assert single_point_result.forces is not None
        assert len(single_point_result.forces) == 3
        assert all(len(f) == 3 for f in single_point_result.forces)
    else:
        assert single_point_result.forces is None

def test_result_energy(single_point_result, properties):
    if "energy" in properties:
        assert single_point_result.energy is not None
        assert isinstance(single_point_result.energy, float)
    else:
        assert single_point_result.energy is None
