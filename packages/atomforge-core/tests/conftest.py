import pytest

from atomforge_core.structure import StructureData


@pytest.fixture
def example_structure():
    return StructureData(
        positions=[[4.5, 0, 0], [5.5, 0, 0]],
        cell=[[10, 0, 0], [0, 10, 0], [0, 0, 10]],
        numbers=[1, 8],
        pbc=[False, False, False],
    )

