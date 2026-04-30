from __future__ import annotations

from abc import abstractmethod

from pydantic import BaseModel, ConfigDict

from atomforge_core.property import Property
from typing import Literal, TypeVar


class TaskSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_default=True)
    execution_policy: Literal["default", "prefer_model_override", "require_model_override"] = "default"

    @abstractmethod
    def required_model_properties(self) -> frozenset[Property]:
        raise NotImplementedError

TaskSpecT = TypeVar("TaskSpecT", bound=TaskSpec)
