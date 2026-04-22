import pytest
from ase import Atoms

from atomforge.backend.subprocess.backend import SubprocessBackend
from atomforge.model.ase_lj import LennardJones
from atomforge.task.bfgs import BFGS, BFGSResult


@pytest.fixture(scope="module")
def bfgs_task():
    atoms = Atoms(
        "HOH", positions=[[0, 0, 0], [0, 0, 1], [1, 0, 0]], cell=[10, 10, 10], pbc=False
    )
    task = BFGS(structure=atoms)

    return task


@pytest.fixture(scope="module")
def bfgs_result(backend, bfgs_task) -> BFGSResult:
    from atomforge.task.core.resources import ExecutionResources

    resources = ExecutionResources(accelerator="cpu", precision="f64")
    model = LennardJones()
    result = backend.execute(bfgs_task, model, resources)
    return result


def test_result_kind(bfgs_result: BFGSResult):
    assert bfgs_result.kind == "bfgs"


def test_result_forces(bfgs_result: BFGSResult):
    assert bfgs_result.forces is not None
    assert len(bfgs_result.forces) == 3
    assert all(len(f) == 3 for f in bfgs_result.forces)
