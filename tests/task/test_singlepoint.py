import pytest
from atomforge.task.singlepoint import SinglePoint, SinglePointExecutor
from atomforge.model.base.property import Property

def test_single_point_creation(example_structure):
    task = SinglePoint(structure=example_structure)
    assert task.structure == example_structure
    assert task.requested_properties == frozenset([Property.ENERGY, Property.FORCES])

def test_single_point_creation_with_properties(example_structure):
    task = SinglePoint(structure=example_structure, properties=[Property.ENERGY])
    assert task.structure == example_structure
    assert task.requested_properties == frozenset([Property.ENERGY])

def test_single_point_creation_with_string_properties(example_structure):
    task = SinglePoint(structure=example_structure, properties=["energy"])
    assert task.structure == example_structure
    assert task.requested_properties == frozenset([Property.ENERGY])

def test_single_point_creation_with_empty_properties(example_structure):
    with pytest.raises(ValueError):
        SinglePoint(structure=example_structure, properties=[])

def test_single_point_creation_with_invalid_string_properties(example_structure):
    with pytest.raises(ValueError):
        SinglePoint(structure=example_structure, properties=["invalid_property"])

def test_single_point_creation_with_mixed_properties(example_structure):
    with pytest.raises(ValueError):
        SinglePoint(structure=example_structure, properties=[Property.ENERGY, "forces", "invalid_property"])

def test_single_point_creation_with_incapable_property(example_structure):
    with pytest.raises(ValueError):
        SinglePoint(structure=example_structure, properties=[Property.ENERGY, Property.FORCES, Property.STRESS])

def test_single_point_creation_with_all_incapable_properties(example_structure):
    with pytest.raises(ValueError):
        SinglePoint(structure=example_structure, properties=[Property.STRESS])

def test_single_point_creation_with_duplicate_properties(example_structure):
    task = SinglePoint(structure=example_structure, properties=[Property.ENERGY, Property.ENERGY])
    assert task.structure == example_structure
    assert task.requested_properties == frozenset([Property.ENERGY])

def test_single_point_creation_with_mixed_case_string_properties(example_structure):
    task = SinglePoint(structure=example_structure, properties=["Energy", "Forces"])
    assert task.structure == example_structure
    assert task.requested_properties == frozenset([Property.ENERGY, Property.FORCES])

def test_single_point_to_spec(example_structure):
    task = SinglePoint(structure=example_structure, properties=[Property.ENERGY])
    spec = task.to_spec()
    assert spec.kind == "single_point"
    assert spec.structure == example_structure.to_message()
    assert spec.properties == frozenset([Property.ENERGY])

def test_single_point_executor(lj_executor, example_structure):
    task = SinglePoint(structure=example_structure, properties=[Property.ENERGY, Property.FORCES])
    spec = task.to_spec()
    result = SinglePointExecutor().execute(spec, lj_executor)
    assert result.kind == "single_point"
    assert isinstance(result.energy, float)
    assert isinstance(result.forces, list) and all(isinstance(f, list) for f in result.forces)