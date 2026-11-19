"""Describe a ``ModelResult`` as facts about types and shapes, not a verdict.

A description is JSON-ready, so it survives the transport from the worker:

- every value has ``type`` (the class name, with its module unless it is a
  builtin) and, except lists, ``is_float`` (an instance of ``float``, which
  includes ``numpy.float64``);
- a value with ``shape`` and ``dtype`` (arrays, numpy scalars other than
  ``float64``) also has those;
- a list has ``length``, ``items`` (the description shared by every item, or
  ``None`` if they differ or there are none) and ``item_types``;
- a field (``describe_field``) also has ``finite``: whether every float in it
  is finite, or ``None`` if it holds no floats.
"""

import math
from dataclasses import fields as dataclass_fields
from typing import Any

from atomforge_core.model.result import ModelResult
from atomforge_core.property import Property
from atomforge_core.task.executability import CompatibilityCheck
from atomforge_core.task.executor import (
    TaskExecutionContext,
    TaskExecutor,
    require_model_executor,
)

from atomforge_builtins.task.describe_model_result.result import (
    DescribeModelResultResult,
)
from atomforge_builtins.task.describe_model_result.spec import DescribeModelResult

DESCRIBED_FIELDS = tuple(p.value for p in Property)


def _type_name(value: Any) -> str:
    cls = type(value)
    module = cls.__module__
    if module == "builtins":
        return cls.__qualname__
    return f"{module.split('.')[0]}.{cls.__qualname__}"


def _has_array_shape(value: Any) -> bool:
    return hasattr(value, "shape") and hasattr(value, "dtype")


def describe_value(value: Any) -> dict[str, Any]:
    if isinstance(value, list):
        items = [describe_value(item) for item in value]
        common = items[0] if items and all(i == items[0] for i in items) else None
        return {
            "type": "list",
            "length": len(value),
            "items": common,
            "item_types": sorted({_type_name(item) for item in value}),
        }
    described: dict[str, Any] = {
        "type": _type_name(value),
        "is_float": isinstance(value, float),
    }
    if not described["is_float"] and _has_array_shape(value):
        described["shape"] = [int(n) for n in value.shape]
        described["dtype"] = str(value.dtype)
    return described


def _finiteness(value: Any) -> list[bool]:
    """One entry per float, or per array of floats, in the value."""
    if isinstance(value, float):
        return [math.isfinite(value)]
    if isinstance(value, (list, tuple)):
        return [ok for item in value for ok in _finiteness(item)]
    if _has_array_shape(value):
        import numpy as np

        array = np.asarray(value)
        if np.issubdtype(array.dtype, np.floating):
            return [bool(np.isfinite(array).all())]
    return []


def describe_field(value: Any) -> dict[str, Any]:
    finite = _finiteness(value)
    return {**describe_value(value), "finite": all(finite) if finite else None}


def describe_model_result(result: ModelResult) -> dict[str, dict[str, Any]]:
    """Describe the property fields of the result that have a value."""
    names = [f.name for f in dataclass_fields(result) if f.name in DESCRIBED_FIELDS]
    return {
        name: describe_field(getattr(result, name))
        for name in names
        if getattr(result, name) is not None
    }


class DescribeModelResultExecutor(
    TaskExecutor[DescribeModelResult, DescribeModelResultResult]
):
    @classmethod
    def check_compatibility(
        cls, spec: DescribeModelResult, context: TaskExecutionContext
    ) -> CompatibilityCheck:
        return CompatibilityCheck(ok=True)

    def execute(
        self, spec: DescribeModelResult, context: TaskExecutionContext
    ) -> DescribeModelResultResult:
        model_executor = require_model_executor(context, task_kind=spec.kind)
        result = model_executor.compute(spec.structure, spec.properties)
        return DescribeModelResultResult(fields=describe_model_result(result))
