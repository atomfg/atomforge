from abc import abstractmethod
from typing import Protocol

from atomforge.model.base.executor import ModelExecutor

from .result import TaskResult
from .spec import TaskSpec


class TaskExecutor(Protocol):
    @abstractmethod
    def execute(self, spec: TaskSpec, model_executor: ModelExecutor) -> TaskResult:
        raise NotImplementedError
