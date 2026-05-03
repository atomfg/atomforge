from __future__ import annotations

from abc import abstractmethod
from typing import ClassVar, TypeVar

from pydantic import BaseModel, ConfigDict

from atomforge_core.property import Property
from atomforge_core.task.execution_policy import ExecutionPolicy


class TaskSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_default=True)
    # Task-level execution contract. Subclasses may override this as a class
    # attribute, but it is not part of the serialized task payload.
    requires_model: ClassVar[bool] = True
    execution_policy: ExecutionPolicy = ExecutionPolicy.DEFAULT

    @abstractmethod
    def required_model_properties(self) -> frozenset[Property]:
        raise NotImplementedError

TaskSpecT = TypeVar("TaskSpecT", bound=TaskSpec)
