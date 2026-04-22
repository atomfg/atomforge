import pytest
import numpy as np
from atomforge.model.core.property import Property
from atomforge.structure import StructureMessage
from atomforge.task.bfgs import BFGS, BFGSExecutor, BFGSResult

@pytest.fixture
def bfgs_task(example_structure) -> BFGS:
    task = BFGS(structure=example_structure, fmax=0.5)
    return task

@pytest.fixture
def bfgs_executor() -> BFGSExecutor:
    executor = BFGSExecutor()
    return executor

@pytest.fixture
def bfgs_result(bfgs_task, bfgs_executor, model_executor) -> BFGSResult:
    result = bfgs_executor.execute(bfgs_task, model_executor)
    return result

def test_bfgs_kind(bfgs_task):
    assert bfgs_task.kind == "bfgs"

def test_bfgs_required_properties(bfgs_task):
    required_props = bfgs_task.required_model_properties()
    assert isinstance(required_props, frozenset)
    assert Property.ENERGY in required_props
    assert Property.FORCES in required_props

def test_bfgs_structure_message(bfgs_task, example_structure):
    assert isinstance(bfgs_task.structure, StructureMessage)
    assert bfgs_task.structure == example_structure.to_message()

def test_restored_structure(bfgs_task, example_structure):
    restored = bfgs_task.get_structure()
    assert np.array_equal(restored.positions, example_structure.positions)
    assert np.array_equal(restored.cell, example_structure.cell)
    assert restored.species == example_structure.species
    assert restored.pbc == example_structure.pbc

def test_bfgs_accepts_ase_atoms():
    from ase import Atoms

    atoms = Atoms(
        "Ar2",
        positions=[[0, 0, 0], [1, 0, 0]],
        cell=[10, 10, 10],
        pbc=False,
    )

    task = BFGS(structure=atoms, fmax=0.1)
    assert isinstance(task.structure, StructureMessage)

def test_bfgs_result_type(bfgs_result):
    assert isinstance(bfgs_result, BFGSResult)

def test_bfgs_result_kind(bfgs_result):
    assert bfgs_result.kind == "bfgs"

def test_bfgs_result_structure(bfgs_result, example_structure):
    assert isinstance(bfgs_result.structure, StructureMessage)
    assert bfgs_result.structure != example_structure.to_message()