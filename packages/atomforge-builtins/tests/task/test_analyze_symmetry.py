from importlib.util import find_spec

import pytest

from atomforge_builtins.task.analyze_symmetry import AnalyzeSymmetry, AnalyzeSymmetryResult
from atomforge_builtins.task.analyze_symmetry.executor import AnalyzeSymmetryExecutor
from atomforge_core.structure import StructureData
from atomforge_core.task.executor import TaskExecutionContext

HAS_PYMATGEN = find_spec("pymatgen") is not None and find_spec("ase") is not None


@pytest.fixture
def symmetry_structure():
    return StructureData(
        positions=[[0.0, 0.0, 0.0]],
        cell=[[3.0, 0.0, 0.0], [0.0, 3.0, 0.0], [0.0, 0.0, 3.0]],
        numbers=[14],
        pbc=[True, True, True],
    )


def test_analyze_symmetry_defaults(symmetry_structure):
    task = AnalyzeSymmetry(structure=symmetry_structure)
    assert task.requires_model is False
    assert task.kind == "analyze_symmetry"
    assert task.symprec == 0.01
    assert task.angle_tolerance == 5.0
    assert task.return_primitive is False
    assert task.return_conventional is False
    assert task.required_model_properties() == frozenset()


def test_analyze_symmetry_result_model():
    result = AnalyzeSymmetryResult(
        space_group_symbol="Pm-3m",
        space_group_number=221,
        crystal_system="cubic",
        lattice_type="cubic",
        point_group_symbol="m-3m",
    )
    assert result.kind == "analyze_symmetry"
    assert result.primitive_structure is None
    assert result.conventional_structure is None


@pytest.mark.skipif(not HAS_PYMATGEN, reason="Requires pymatgen and ASE installation")
def test_analyze_symmetry_executor_metadata_only(symmetry_structure):
    task = AnalyzeSymmetry(structure=symmetry_structure)
    result = AnalyzeSymmetryExecutor().execute(task, TaskExecutionContext())
    assert result.kind == "analyze_symmetry"
    assert isinstance(result.space_group_symbol, str)
    assert isinstance(result.space_group_number, int)
    assert isinstance(result.crystal_system, str)
    assert isinstance(result.lattice_type, str)
    assert isinstance(result.point_group_symbol, str)
    assert result.primitive_structure is None
    assert result.conventional_structure is None


@pytest.mark.skipif(not HAS_PYMATGEN, reason="Requires pymatgen and ASE installation")
def test_analyze_symmetry_executor_can_return_primitive(symmetry_structure):
    task = AnalyzeSymmetry(structure=symmetry_structure, return_primitive=True)
    result = AnalyzeSymmetryExecutor().execute(task, TaskExecutionContext())
    assert isinstance(result.primitive_structure, StructureData)
    assert result.conventional_structure is None


@pytest.mark.skipif(not HAS_PYMATGEN, reason="Requires pymatgen and ASE installation")
def test_analyze_symmetry_executor_can_return_conventional(symmetry_structure):
    task = AnalyzeSymmetry(structure=symmetry_structure, return_conventional=True)
    result = AnalyzeSymmetryExecutor().execute(task, TaskExecutionContext())
    assert result.primitive_structure is None
    assert isinstance(result.conventional_structure, StructureData)


@pytest.mark.skipif(not HAS_PYMATGEN, reason="Requires pymatgen and ASE installation")
def test_analyze_symmetry_executor_can_return_both(symmetry_structure):
    task = AnalyzeSymmetry(
        structure=symmetry_structure,
        return_primitive=True,
        return_conventional=True,
    )
    result = AnalyzeSymmetryExecutor().execute(task, TaskExecutionContext())
    assert isinstance(result.primitive_structure, StructureData)
    assert isinstance(result.conventional_structure, StructureData)
