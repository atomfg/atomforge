import pytest
from importlib.util import find_spec

from atomforge_builtins.task.optimize import (
    FixAtomsConstraint,
    FixCartesianConstraint,
    Optimize,
    OptimizeResult,
)
from atomforge_builtins.task.optimize.executor import (
    OptimizeExecutor,
    constraint_to_ase,
    optimizer_class_for,
)
from atomforge_core.property import Property
from atomforge_core.structure import StructureData

HAS_ASE = find_spec("ase") is not None


@pytest.fixture
def optimize_task(example_structure) -> Optimize:
    return Optimize(structure=example_structure)


def test_optimize_defaults(optimize_task):
    assert optimize_task.kind == "optimize"
    assert optimize_task.fmax == 0.05
    assert optimize_task.optimizer == "bfgs"
    assert optimize_task.max_steps is None
    assert optimize_task.constraints == ()


def test_optimize_required_properties(optimize_task):
    required_props = optimize_task.required_model_properties()
    assert isinstance(required_props, frozenset)
    assert required_props == frozenset({Property.ENERGY, Property.FORCES})


def test_optimize_structure_message(optimize_task, example_structure):
    assert isinstance(optimize_task.structure, StructureData)
    assert optimize_task.structure == example_structure


def test_fix_atoms_constraint_model():
    constraint = FixAtomsConstraint(indices=(0, 2))
    assert constraint.type == "fix_atoms"
    assert constraint.indices == (0, 2)


def test_fix_cartesian_constraint_model():
    constraint = FixCartesianConstraint(indices=(1,), mask=(True, False, True))
    assert constraint.type == "fix_cartesian"
    assert constraint.indices == (1,)
    assert constraint.mask == (True, False, True)


@pytest.mark.parametrize(
    "constraint_payload",
    [
        {"type": "fix_atoms", "indices": ()},
        {"type": "fix_atoms", "indices": (0, 0)},
        {"type": "fix_cartesian", "indices": ()},
        {"type": "fix_cartesian", "indices": (1, 1), "mask": (True, False, True)},
    ],
)
def test_constraint_indices_validation(example_structure, constraint_payload):
    with pytest.raises(ValueError):
        Optimize(structure=example_structure, constraints=(constraint_payload,))


def test_constraint_mask_validation(example_structure):
    with pytest.raises(ValueError):
        Optimize(
            structure=example_structure,
            constraints=(
                {"type": "fix_cartesian", "indices": (0,), "mask": (True, False)},
            ),
        )


@pytest.mark.parametrize("optimizer_name", ["bfgs", "lbfgs", "fire"])
def test_optimizer_validation(example_structure, optimizer_name):
    task = Optimize(structure=example_structure, optimizer=optimizer_name)
    assert task.optimizer == optimizer_name


def test_optimizer_validation_rejects_unknown(example_structure):
    with pytest.raises(ValueError):
        Optimize(structure=example_structure, optimizer="BFGS")


@pytest.mark.skipif(not HAS_ASE, reason="Requires ASE installation")
def test_optimizer_class_selection():
    assert optimizer_class_for("bfgs").__name__ == "BFGS"
    assert optimizer_class_for("lbfgs").__name__ == "LBFGS"
    assert optimizer_class_for("fire").__name__ == "FIRE"


@pytest.mark.skipif(not HAS_ASE, reason="Requires ASE installation")
def test_constraint_to_ase_fix_atoms():
    ase_constraint = constraint_to_ase(FixAtomsConstraint(indices=(0, 1)))
    assert ase_constraint.__class__.__name__ == "FixAtoms"


@pytest.mark.skipif(not HAS_ASE, reason="Requires ASE installation")
def test_constraint_to_ase_fix_cartesian():
    ase_constraint = constraint_to_ase(
        FixCartesianConstraint(indices=(0,), mask=(True, False, True))
    )
    assert ase_constraint.__class__.__name__ == "FixCartesian"


@pytest.fixture
def optimize_executor() -> OptimizeExecutor:
    return OptimizeExecutor()


@pytest.mark.skipif(not HAS_ASE, reason="Requires ASE installation")
def test_optimize_result_type(optimize_task, optimize_executor, model_executor):
    result = optimize_executor.execute(optimize_task, model_executor)
    assert isinstance(result, OptimizeResult)


@pytest.mark.skipif(not HAS_ASE, reason="Requires ASE installation")
def test_optimize_result_fields(optimize_task, optimize_executor, model_executor):
    result = optimize_executor.execute(optimize_task, model_executor)
    assert result.kind == "optimize"
    assert isinstance(result.structure, StructureData)
    assert isinstance(result.energy, float)
    assert len(result.forces) == 2
    assert isinstance(result.converged, bool)
    assert isinstance(result.steps, int)


@pytest.mark.skipif(not HAS_ASE, reason="Requires ASE installation")
def test_optimize_max_steps_forwarding(example_structure, optimize_executor, model_executor):
    result = optimize_executor.execute(
        Optimize(structure=example_structure, fmax=0.5, max_steps=1),
        model_executor,
    )
    assert result.steps <= 1
