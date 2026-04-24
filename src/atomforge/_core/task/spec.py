from __future__ import annotations

from abc import abstractmethod

from pydantic import BaseModel, ConfigDict

from atomforge._core.property import Property
from typing import TypeVar


class TaskSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_default=True)

    @abstractmethod
    def required_model_properties(self) -> frozenset[Property]:
        raise NotImplementedError

TaskSpecT = TypeVar("TaskSpecT", bound=TaskSpec)
