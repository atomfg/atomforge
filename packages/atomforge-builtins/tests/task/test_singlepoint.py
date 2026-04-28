import pytest

from atomforge_builtins.model.nodep_model import NoDep, NoDepExecutor
from atomforge_builtins.task.singlepoint import SinglePoint, SinglePointExecutor
from atomforge_core.property import Property
from atomforge_core.resources.resource_models import ResolvedResources
from atomforge_core.structure import StructureData


@pytest.fixture
def nodep_executor():
    spec = NoDep()
    resources = ResolvedResources(accelerator="cpu", precision=None, messages={})
    return NoDepExecutor(spec=spec, resolved_resources=resources)


def test_single_point_creation(example_structure):
    task = SinglePoint(structure=example_structure)
    assert isinstance(task.structure, StructureData)
    assert task.structure == example_structure
    assert task.properties == frozenset([Property.ENERGY, Property.FORCES])
    restored = task.structure
    assert restored.positions == example_structure.positions
    assert restored.cell == example_structure.cell
    assert restored.numbers == example_structure.numbers
    assert restored.pbc == example_structure.pbc
    assert task.required_model_properties() == frozenset(
        [Property.ENERGY, Property.FORCES]
    )


def test_single_point_creation_with_properties(example_structure):
    task = SinglePoint(structure=example_structure, properties=[Property.ENERGY])
    assert task.structure == example_structure
    assert task.properties == frozenset([Property.ENERGY])


def test_single_point_creation_with_string_properties(example_structure):
    task = SinglePoint(structure=example_structure, properties=["energy"])
    assert task.structure == example_structure
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
    assert task.structure == example_structure
    assert task.properties == frozenset([Property.ENERGY])


def test_single_point_creation_with_mixed_case_string_properties(example_structure):
    task = SinglePoint(structure=example_structure, properties=["Energy", "Forces"])
    assert task.properties == frozenset([Property.ENERGY, Property.FORCES])


def test_single_point_executor(nodep_executor, example_structure):
    task = SinglePoint(
        structure=example_structure, properties=[Property.ENERGY, Property.FORCES]
    )
    result = SinglePointExecutor().execute(task, nodep_executor)
    assert result.kind == "single_point"
    assert isinstance(result.energy, float)
    assert isinstance(result.forces, list) and all(
        isinstance(f, list) for f in result.forces
    )

