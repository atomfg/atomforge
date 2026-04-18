from abc import abstractmethod
from typing import Protocol, TypeVar

from atomforge.model.base.executor import ModelExecutor

from .result import TaskResult
from .spec import TaskSpec


TaskSpecT = TypeVar("TaskSpecT", bound=TaskSpec)
TaskResultT = TypeVar("TaskResultT", bound=TaskResult)


class TaskExecutor(Protocol[TaskSpecT, TaskResultT]):
    @abstractmethod
    def execute(self, spec: TaskSpecT, model_executor: ModelExecutor) -> TaskResultT:
        raise NotImplementedError
