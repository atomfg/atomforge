from atomforge.structure import StructureData

def compare_structures(struct1, struct2):
    assert struct1.positions.tolist() == struct2.positions.tolist()
    assert struct1.cell.tolist() == struct2.cell.tolist()
    assert struct1.numbers == struct2.numbers
    assert struct1.pbc == struct2.pbc