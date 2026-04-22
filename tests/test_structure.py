from atomforge.structure import Structure

def compare_structures(struct1, struct2):
    assert struct1.positions.tolist() == struct2.positions.tolist()
    assert struct1.cell.tolist() == struct2.cell.tolist()
    assert struct1.species == struct2.species
    assert struct1.pbc == struct2.pbc


def test_structure_to_message(example_structure):
    message = example_structure.to_message()
    assert message.positions == example_structure.positions.tolist()
    assert message.cell == example_structure.cell.tolist()
    assert message.species == example_structure.species
    assert message.pbc == example_structure.pbc


def test_structure_to_ase(example_structure):
    atoms = example_structure.to_ase()
    assert atoms.get_positions().tolist() == example_structure.positions.tolist()
    assert atoms.get_cell().array.tolist() == example_structure.cell.tolist()
    assert atoms.get_chemical_symbols() == example_structure.species
    assert atoms.get_pbc().tolist() == example_structure.pbc


def test_ase_roundtrip(example_structure):
    atoms = example_structure.to_ase()
    new_structure = Structure.from_ase(atoms)
    compare_structures(new_structure, example_structure)


def test_message_roundtrip(example_structure):
    message = example_structure.to_message()
    new_structure = message.to_structure()
    compare_structures(new_structure, example_structure)
