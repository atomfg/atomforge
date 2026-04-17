import pytest
from atomforge.structure import Structure


@pytest.fixture
def example_structure():
    return Structure(
        positions=[[0, 0, 0], [1, 1, 1]],
        cell=[[2, 0, 0], [0, 2, 0], [0, 0, 2]],
        species=["H", "O"],
        pbc=[True, True, True],
    )


def compare_structures(struct1, struct2):
    assert struct1.positions.tolist() == struct2.positions.tolist()
    assert struct1.cell.tolist() == struct2.cell.tolist()
    assert struct1.species == struct2.species
    assert struct1.pbc == struct2.pbc


def test_structure_to_message(example_structure):
    message = example_structure.to_message()
    assert message.positions == [[0, 0, 0], [1, 1, 1]]
    assert message.cell == [[2, 0, 0], [0, 2, 0], [0, 0, 2]]
    assert message.species == ["H", "O"]
    assert message.pbc == [True, True, True]


def test_structure_to_ase(example_structure):
    atoms = example_structure.to_ase()
    assert atoms.get_positions().tolist() == [[0, 0, 0], [1, 1, 1]]
    assert atoms.get_cell().array.tolist() == [[2, 0, 0], [0, 2, 0], [0, 0, 2]]
    assert atoms.get_chemical_symbols() == ["H", "O"]
    assert atoms.get_pbc().tolist() == [True, True, True]


def test_ase_roundtrip(example_structure):
    atoms = example_structure.to_ase()
    new_structure = Structure.from_ase(atoms)
    compare_structures(new_structure, example_structure)


def test_message_roundtrip(example_structure):
    message = example_structure.to_message()
    new_structure = message.to_structure()
    compare_structures(new_structure, example_structure)
