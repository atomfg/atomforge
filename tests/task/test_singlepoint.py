import pytest
import numpy as np
from atomforge.task.singlepoint import SinglePoint, SinglePointExecutor
from atomforge.model.core.property import Property
from atomforge.structure import StructureMessage


def test_single_point_creation(example_structure):
    task = SinglePoint(structure=example_structure)
    assert isinstance(task.structure, StructureMessage)
    assert task.structure == example_structure.to_message()
    assert task.properties == frozenset([Property.ENERGY, Property.FORCES])
    restored = task.get_structure()
    assert np.array_equal(restored.positions, example_structure.positions)
    assert np.array_equal(restored.cell, example_structure.cell)
    assert restored.species == example_structure.species
    assert restored.pbc == example_structure.pbc
    assert task.required_model_properties() == frozenset(
        [Property.ENERGY, Property.FORCES]
    )


def test_single_point_creation_with_properties(example_structure):
    task = SinglePoint(structure=example_structure, properties=[Property.ENERGY])
    assert task.structure == example_structure.to_message()
    assert task.properties == frozenset([Property.ENERGY])


def test_single_point_creation_with_string_properties(example_structure):
    task = SinglePoint(structure=example_structure, properties=["energy"])
    assert task.structure == example_structure.to_message()
    assert task.properties == frozenset([Property.ENERGY])


def test_single_point_creation_with_empty_properties(example_structure):
    with pytest.raises(ValueError):
        SinglePoint(structure=example_structure, properties=[])


def test_single_point_creation_with_invalid_string_properties(example_structure):
    with pytest.raises(ValueError):
        SinglePoint(structure=example_structure, properties=["invalid_property"])


def test_single_point_creation_with_mixed_properties(example_structure):
    with pytest.raises(ValueError):
        SinglePoint(
            structure=example_structure,
            properties=[Property.ENERGY, "forces", "invalid_property"],
        )


def test_single_point_creation_with_incapable_property(example_structure):
    with pytest.raises(ValueError):
        SinglePoint(
            structure=example_structure,
            properties=[Property.ENERGY, Property.FORCES, Property.STRESS],
        )


def test_single_point_creation_with_all_incapable_properties(example_structure):
    with pytest.raises(ValueError):
        SinglePoint(structure=example_structure, properties=[Property.STRESS])


def test_single_point_creation_with_duplicate_properties(example_structure):
    task = SinglePoint(
        structure=example_structure, properties=[Property.ENERGY, Property.ENERGY]
    )
    assert task.structure == example_structure.to_message()
    assert task.properties == frozenset([Property.ENERGY])


def test_single_point_creation_with_mixed_case_string_properties(example_structure):
    task = SinglePoint(structure=example_structure, properties=["Energy", "Forces"])
    assert task.properties == frozenset([Property.ENERGY, Property.FORCES])


def test_single_point_accepts_structure_message(example_structure):
    task = SinglePoint(
        structure=example_structure.to_message(), properties=[Property.ENERGY]
    )
    assert task.structure == example_structure.to_message()
    restored = task.get_structure()
    assert np.array_equal(restored.positions, example_structure.positions)
    assert np.array_equal(restored.cell, example_structure.cell)
    assert restored.species == example_structure.species
    assert restored.pbc == example_structure.pbc


def test_single_point_accepts_ase_atoms():
    from ase import Atoms

    atoms = Atoms(
        "HOH",
        positions=[[0, 0, 0], [0, 0, 1], [1, 0, 0]],
        cell=[10, 10, 10],
        pbc=False,
    )

    task = SinglePoint(structure=atoms, properties=["forces"])
    assert isinstance(task.structure, StructureMessage)
    assert task.properties == frozenset([Property.FORCES])
    assert task.get_structure().species == ["H", "O", "H"]


def test_single_point_executor(lj_executor, example_structure):
    task = SinglePoint(
        structure=example_structure, properties=[Property.ENERGY, Property.FORCES]
    )
    result = SinglePointExecutor().execute(task, lj_executor)
    assert result.kind == "single_point"
    assert isinstance(result.energy, float)
    assert isinstance(result.forces, list) and all(
        isinstance(f, list) for f in result.forces
    )
