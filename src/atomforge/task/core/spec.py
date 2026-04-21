from __future__ import annotations

from abc import abstractmethod

from pydantic import BaseModel, ConfigDict

from atomforge.model.core.property import Property
from atomforge.structure import Structure, StructureMessage
from typing import TypeVar


class TaskSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_default=True)

    @abstractmethod
    def required_model_properties(self) -> frozenset[Property]:
        raise NotImplementedError

    def get_structure(self, field_name: str = "structure") -> Structure:
        value = getattr(self, field_name)
        if not isinstance(value, StructureMessage):
            raise TypeError(
                f"Field '{field_name}' is not a StructureMessage on {type(self).__name__}"
            )
        return value.to_structure()

TaskSpecT = TypeVar("TaskSpecT", bound=TaskSpec)
