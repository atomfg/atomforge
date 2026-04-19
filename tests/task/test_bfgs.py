import numpy as np
from atomforge.model.core.property import Property
from atomforge.structure import StructureMessage
from atomforge.task.bfgs import BFGS


def test_bfgs_creation(example_structure):
    task = BFGS(structure=example_structure)
    assert task.kind == "bfgs"
    assert isinstance(task.structure, StructureMessage)
    assert task.structure == example_structure.to_message()
    assert task.fmax == 0.05
    restored = task.get_structure()
    assert np.array_equal(restored.positions, example_structure.positions)
    assert np.array_equal(restored.cell, example_structure.cell)
    assert restored.species == example_structure.species
    assert restored.pbc == example_structure.pbc
    assert task.required_model_properties() == frozenset(
        {Property.ENERGY, Property.FORCES}
    )


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
    assert task.fmax == 0.1
    assert task.get_structure().species == ["Ar", "Ar"]
