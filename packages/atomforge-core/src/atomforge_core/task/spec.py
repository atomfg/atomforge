from __future__ import annotations

from abc import abstractmethod

from pydantic import BaseModel, ConfigDict

from atomforge_core.property import Property
from atomforge_core.task.execution_policy import ExecutionPolicy
from typing import TypeVar


class TaskSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_default=True)
    execution_policy: ExecutionPolicy = ExecutionPolicy.DEFAULT

    @abstractmethod
    def required_model_properties(self) -> frozenset[Property]:
        raise NotImplementedError

TaskSpecT = TypeVar("TaskSpecT", bound=TaskSpec)
