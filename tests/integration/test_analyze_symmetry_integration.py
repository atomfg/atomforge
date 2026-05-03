from importlib.util import find_spec

import pytest

from atomforge_builtins.task.analyze_symmetry import AnalyzeSymmetry, AnalyzeSymmetryResult
from atomforge_core.structure import StructureData

HAS_PYMATGEN = find_spec("pymatgen") is not None and find_spec("ase") is not None


@pytest.fixture(scope="module")
def symmetry_structure():
    return StructureData(
        positions=[[0.0, 0.0, 0.0]],
        cell=[[3.0, 0.0, 0.0], [0.0, 3.0, 0.0], [0.0, 0.0, 3.0]],
        numbers=[14],
        pbc=[True, True, True],
    )


@pytest.mark.skipif(not HAS_PYMATGEN, reason="Requires pymatgen and ASE installation")
def test_analyze_symmetry_backend_execute_without_model(backend, symmetry_structure):
    task = AnalyzeSymmetry(structure=symmetry_structure, return_conventional=True)
    result = backend.execute(task)

    assert isinstance(result, AnalyzeSymmetryResult)
    assert result.kind == "analyze_symmetry"
    assert isinstance(result.space_group_symbol, str)
    assert result.conventional_structure is not None
