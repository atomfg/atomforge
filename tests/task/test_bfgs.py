import pytest
from atomforge._core.property import Property
from atomforge._core.structure import StructureData
from atomforge._builtins.task.bfgs import BFGS, BFGSExecutor, BFGSResult

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
    assert isinstance(bfgs_task.structure, StructureData)
    assert bfgs_task.structure == example_structure

def test_restored_structure(bfgs_task, example_structure):
    restored = bfgs_task.structure
    assert restored.positions == example_structure.positions
    assert restored.cell == example_structure.cell
    assert restored.numbers == example_structure.numbers
    assert restored.pbc == example_structure.pbc

@pytest.mark.skip('Requires ASE installation')
def test_bfgs_result_type(bfgs_result):
    assert isinstance(bfgs_result, BFGSResult)

@pytest.mark.skip('Requires ASE installation')
def test_bfgs_result_kind(bfgs_result):
    assert bfgs_result.kind == "bfgs"

@pytest.mark.skip('Requires ASE installation')
def test_bfgs_result_structure(bfgs_result, example_structure):
    assert isinstance(bfgs_result.structure, StructureData)
    assert bfgs_result.structure != example_structure