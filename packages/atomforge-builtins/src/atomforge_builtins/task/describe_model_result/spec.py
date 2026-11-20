from typing import Literal

from pydantic import field_validator

from atomforge_core.property import Property
from atomforge_core.structure import StructureData
from atomforge_core.task.spec import TaskSpec

from atomforge_builtins.task.describe_model_result.definitions import KIND


class DescribeModelResult(TaskSpec):
    """Call the model's ``compute`` and describe the raw ``ModelResult``: the
    type and shape of every field that has a value. A diagnostic for plugin
    authors and the result types contract in atomforge-testing.

    With ``later_structure``, compute a second time on it, with the same
    properties, and report which fields of the first result that changed:
    fields that share memory with state the model reuses."""

    kind: Literal["describe_model_result"] = KIND
    structure: StructureData
    properties: frozenset[Property]
    later_structure: StructureData | None = None

    def required_model_properties(self) -> frozenset[Property]:
        return self.properties

    @field_validator("properties")
    @classmethod
    def validate_properties(cls, value: frozenset[Property]):
        if not value:
            raise ValueError("At least one property must be requested.")
        return value
