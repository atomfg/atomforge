"""Acceptance tests for the describe_model_result task (the "Checking model
results in tests, design" entry in the engineering log).

The task calls ``compute`` once and returns a description of the raw
``ModelResult``: facts about each field's types and shapes, not a verdict. The
rules that judge it live in atomforge-testing.
"""

import math

import numpy as np
import pytest

from atomforge_builtins.task.describe_model_result import (
    DescribeModelResult,
    DescribeModelResultResult,
)
from atomforge_builtins.task.describe_model_result.executor import (
    DescribeModelResultExecutor,
    describe_field,
    describe_value,
)
from atomforge_core.model.result import ModelResult
from atomforge_core.property import Property
from atomforge_core.task.executor import TaskExecutionContext
from atomforge_runtime.registry.task.task_registry import TaskRegistry

# describe_value: one value


def test_float_is_described_as_float():
    assert describe_value(1.0) == {"type": "float", "is_float": True}


def test_numpy_float64_keeps_its_type_and_is_a_float():
    assert describe_value(np.float64(1.0)) == {
        "type": "numpy.float64",
        "is_float": True,
    }


def test_numpy_float32_is_not_a_float():
    assert describe_value(np.float32(1.0)) == {
        "type": "numpy.float32",
        "is_float": False,
        "shape": [],
        "dtype": "float32",
    }


def test_int_is_not_a_float():
    assert describe_value(1) == {"type": "int", "is_float": False}


def test_ndarray_reports_shape_and_dtype():
    assert describe_value(np.zeros((5, 3), dtype=np.float32)) == {
        "type": "numpy.ndarray",
        "is_float": False,
        "shape": [5, 3],
        "dtype": "float32",
    }


def test_list_of_floats_has_one_item_description():
    assert describe_value([1.0, 2.0]) == {
        "type": "list",
        "length": 2,
        "items": {"type": "float", "is_float": True},
        "item_types": ["float"],
    }


def test_nested_lists_are_described_recursively():
    row = {
        "type": "list",
        "length": 3,
        "items": {"type": "float", "is_float": True},
        "item_types": ["float"],
    }
    assert describe_value([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]]) == {
        "type": "list",
        "length": 2,
        "items": row,
        "item_types": ["list"],
    }


def test_ragged_rows_have_no_common_item_description():
    described = describe_value([[0.0, 0.0, 0.0], [1.0, 1.0]])
    assert described["items"] is None
    assert described["item_types"] == ["list"]


def test_mixed_items_list_their_types():
    described = describe_value([1.0, 1])
    assert described["items"] is None
    assert described["item_types"] == ["float", "int"]


def test_list_of_ndarray_rows_names_the_row_type():
    described = describe_value(list(np.zeros((2, 3))))
    assert described["items"]["type"] == "numpy.ndarray"


def test_empty_list_has_no_items():
    assert describe_value([]) == {
        "type": "list",
        "length": 0,
        "items": None,
        "item_types": [],
    }


# describe_field: one field, with finiteness


def test_field_with_finite_floats_is_finite():
    assert describe_field([[0.0, 1.0, 2.0]])["finite"] is True


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_field_with_a_non_finite_float_is_not_finite(bad):
    assert describe_field([[0.0, bad, 2.0]])["finite"] is False


def test_finiteness_looks_inside_arrays():
    assert describe_field(np.array([[0.0, np.nan]]))["finite"] is False


def test_field_without_floats_has_no_finiteness():
    assert describe_field([1, 2])["finite"] is None


def test_field_description_extends_the_value_description():
    described = describe_field(1.0)
    assert described == {"type": "float", "is_float": True, "finite": True}


# The task


def test_spec_requires_the_requested_properties(example_structure):
    properties = frozenset({Property.ENERGY, Property.FORCES})
    task = DescribeModelResult(structure=example_structure, properties=properties)
    assert task.required_model_properties() == properties


def test_spec_kind():
    assert DescribeModelResult.model_fields["kind"].default == "describe_model_result"


def test_task_is_registered():
    registration = TaskRegistry.default().get("describe_model_result")
    assert registration.load_executor_class() is DescribeModelResultExecutor


class _FixedResultExecutor:
    """Returns the same ModelResult whatever is requested."""

    def __init__(self, result: ModelResult):
        self.result = result
        self.requests = []

    def compute(self, structure, properties):
        self.requests.append(frozenset(properties))
        return self.result


def _describe(example_structure, result, properties):
    model_executor = _FixedResultExecutor(result)
    described = DescribeModelResultExecutor().execute(
        DescribeModelResult(structure=example_structure, properties=properties),
        TaskExecutionContext(model_executor=model_executor),
    )
    return described, model_executor


def test_task_computes_once_with_the_requested_properties(example_structure):
    properties = frozenset({Property.ENERGY, Property.FORCES})
    _, model_executor = _describe(
        example_structure, ModelResult(energy=1.0), properties
    )
    assert model_executor.requests == [properties]


def test_task_returns_a_describe_model_result_result(example_structure):
    described, _ = _describe(
        example_structure, ModelResult(energy=1.0), frozenset({Property.ENERGY})
    )
    assert isinstance(described, DescribeModelResultResult)


def test_task_describes_every_field_that_has_a_value(example_structure):
    result = ModelResult(energy=1.0, forces=np.zeros((2, 3)), stress=None)
    described, _ = _describe(example_structure, result, frozenset({Property.ENERGY}))
    # forces were not requested, but have a value; stress has none.
    assert set(described.fields) == {"energy", "forces"}


def test_task_describes_the_raw_value(example_structure):
    result = ModelResult(forces=np.zeros((2, 3), dtype=np.float32))
    described, _ = _describe(example_structure, result, frozenset({Property.FORCES}))
    assert described.fields["forces"] == describe_field(result.forces)


def test_task_result_round_trips_through_json(example_structure):
    result = ModelResult(energy=np.float32(1.0), forces=[[0.0, math.nan, 0.0]])
    described, _ = _describe(
        example_structure, result, frozenset({Property.ENERGY, Property.FORCES})
    )
    restored = DescribeModelResultResult.model_validate_json(
        described.model_dump_json()
    )
    assert restored.fields == described.fields


def test_lennard_jones_is_described_as_declared(model_executor, example_structure):
    described = DescribeModelResultExecutor().execute(
        DescribeModelResult(
            structure=example_structure,
            properties=frozenset({Property.ENERGY, Property.FORCES}),
        ),
        TaskExecutionContext(model_executor=model_executor),
    )
    forces = described.fields["forces"]
    assert (forces["type"], forces["dtype"], forces["shape"]) == (
        "numpy.ndarray",
        "float64",
        [len(example_structure.numbers), 3],
    )


# A later compute ("Model results as float64 arrays, design"): the task can
# compute a second time on a later structure and report which fields of the
# first result changed, i.e. shared memory with state the model reused.


def _moved(structure):
    positions = [list(p) for p in structure.positions]
    positions[0][0] += 0.1
    return structure.model_copy(update={"positions": positions})


class _StructureRecordingExecutor:
    """Fresh arrays from the positions on every call."""

    def __init__(self):
        self.calls = []

    def compute(self, structure, properties):
        self.calls.append((structure, frozenset(properties)))
        return ModelResult(
            energy=float(np.sum(structure.positions)),
            forces=np.array(structure.positions, dtype=np.float64),
        )


class _BufferReusingExecutor:
    """Writes every result into the same forces array."""

    def __init__(self):
        self.forces = None

    def compute(self, structure, properties):
        positions = np.array(structure.positions, dtype=np.float64)
        if self.forces is None:
            self.forces = np.empty_like(positions)
        self.forces[...] = positions
        return ModelResult(energy=1.0, forces=self.forces)


class _ListReusingExecutor:
    """Writes every result into the same nested list."""

    def __init__(self):
        self.forces = None

    def compute(self, structure, properties):
        if self.forces is None:
            self.forces = [[0.0, 0.0, 0.0] for _ in structure.numbers]
        for row, position in zip(self.forces, structure.positions):
            row[:] = [float(x) for x in position]
        return ModelResult(energy=1.0, forces=self.forces)


class _NanForcesExecutor:
    def compute(self, structure, properties):
        return ModelResult(forces=np.full((len(structure.numbers), 3), np.nan))


def _describe_with_later(example_structure, model_executor):
    return DescribeModelResultExecutor().execute(
        DescribeModelResult(
            structure=example_structure,
            properties=frozenset({Property.ENERGY, Property.FORCES}),
            later_structure=_moved(example_structure),
        ),
        TaskExecutionContext(model_executor=model_executor),
    )


def test_spec_has_no_later_structure_by_default(example_structure):
    task = DescribeModelResult(
        structure=example_structure, properties=frozenset({Property.ENERGY})
    )
    assert task.later_structure is None


def test_without_a_later_structure_changes_are_not_checked(example_structure):
    described, _ = _describe(
        example_structure, ModelResult(energy=1.0), frozenset({Property.ENERGY})
    )
    assert described.changed_by_later_compute is None


def test_later_structure_is_computed_second(example_structure):
    model_executor = _StructureRecordingExecutor()
    _describe_with_later(example_structure, model_executor)
    structures = [structure for structure, _ in model_executor.calls]
    assert structures == [example_structure, _moved(example_structure)]


def test_later_compute_requests_the_same_properties(example_structure):
    model_executor = _StructureRecordingExecutor()
    _describe_with_later(example_structure, model_executor)
    properties = frozenset({Property.ENERGY, Property.FORCES})
    assert [p for _, p in model_executor.calls] == [properties, properties]


def test_the_first_result_is_described(example_structure):
    described = _describe_with_later(example_structure, _StructureRecordingExecutor())
    first = describe_field(np.array(example_structure.positions, dtype=float))
    assert described.fields["forces"] == first


def test_fresh_results_are_not_changed(example_structure):
    described = _describe_with_later(example_structure, _StructureRecordingExecutor())
    assert described.changed_by_later_compute == []


def test_a_reused_array_is_changed(example_structure):
    described = _describe_with_later(example_structure, _BufferReusingExecutor())
    assert described.changed_by_later_compute == ["forces"]


def test_a_reused_list_is_changed(example_structure):
    described = _describe_with_later(example_structure, _ListReusingExecutor())
    assert described.changed_by_later_compute == ["forces"]


def test_nan_values_that_stay_nan_are_not_changed(example_structure):
    described = _describe_with_later(example_structure, _NanForcesExecutor())
    assert described.changed_by_later_compute == []


def test_later_compute_round_trips_through_json(example_structure):
    described = _describe_with_later(example_structure, _BufferReusingExecutor())
    restored = DescribeModelResultResult.model_validate_json(
        described.model_dump_json()
    )
    assert restored.changed_by_later_compute == ["forces"]
