import pytest

from atomforge_builtins.model.ase_lj import LennardJones
from atomforge_builtins.task.optimize import FixAtomsConstraint, Optimize, OptimizeResult
from atomforge_core.structure import StructureData


@pytest.fixture(scope="module")
def optimize_structure():
    return StructureData(
        positions=[[4.5, 0, 0], [5.5, 0, 0]],
        cell=[[10, 0, 0], [0, 10, 0], [0, 0, 10]],
        numbers=[1, 8],
        pbc=[False, False, False],
    )


@pytest.fixture(scope="module")
def optimize_task(optimize_structure):
    return Optimize(structure=optimize_structure, fmax=0.5)


@pytest.fixture(scope="module")
def optimize_result(backend, optimize_task) -> OptimizeResult:
    from atomforge_core.resources.resource_models import ExecutionResources

    resources = ExecutionResources(accelerator="cpu", precision="f64")
    model = LennardJones()
    return backend.execute(optimize_task, model, resources)


def test_optimize_result_kind(optimize_result: OptimizeResult):
    assert optimize_result.kind == "optimize"


def test_optimize_result_forces(optimize_result: OptimizeResult):
    assert optimize_result.forces is not None
    assert len(optimize_result.forces) == 2
    assert all(len(f) == 3 for f in optimize_result.forces)


def test_optimize_result_convergence_fields(optimize_result: OptimizeResult):
    assert isinstance(optimize_result.converged, bool)
    assert isinstance(optimize_result.steps, int)


@pytest.fixture(scope="module")
def constrained_optimize_result(backend, optimize_structure) -> OptimizeResult:
    from atomforge_core.resources.resource_models import ExecutionResources

    resources = ExecutionResources(accelerator="cpu", precision="f64")
    model = LennardJones()
    task = Optimize(
        structure=optimize_structure,
        fmax=0.5,
        constraints=(FixAtomsConstraint(indices=(0,)),),
    )
    return backend.execute(task, model, resources)


def test_optimize_fix_atoms_constraint_holds_position(
    constrained_optimize_result: OptimizeResult, optimize_structure: StructureData
):
    assert constrained_optimize_result.structure.positions[0] == optimize_structure.positions[0]
