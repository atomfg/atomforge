from abc import abstractmethod
from typing import Protocol

from atomforge.model.base import Model
from atomforge.task.base import TaskResult, TaskSpec


class TaskExecutor(Protocol):
    @abstractmethod
    def execute(self, spec: TaskSpec, model: Model) -> TaskResult:
        raise NotImplementedError
