from pydantic import BaseModel, ConfigDict
from typing import TypeVar


class TaskResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

TaskResultT = TypeVar("TaskResultT", bound=TaskResult)
