from typing import Literal

from pydantic import field_validator

from atomforge_core.property import Property
from atomforge_core.structure import StructureData
from atomforge_core.task.spec import TaskSpec

from atomforge_builtins.task.describe_model_result.definitions import KIND


class DescribeModelResult(TaskSpec):
    """Call the model's ``compute`` once and describe the raw ``ModelResult``:
    the type and shape of every field that has a value. A diagnostic for
    plugin authors and the result types contract in atomforge-testing."""

    kind: Literal["describe_model_result"] = KIND
    structure: StructureData
    properties: frozenset[Property]

    def required_model_properties(self) -> frozenset[Property]:
        return self.properties

    @field_validator("properties")
    @classmethod
    def validate_properties(cls, value: frozenset[Property]):
        if not value:
            raise ValueError("At least one property must be requested.")
        return value
