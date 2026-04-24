from abc import abstractmethod
from typing import Protocol
import typing

from atomforge._core.model.executor import ModelExecutor

from atomforge._core.task.result import TaskResultT
from atomforge._core.task.spec import TaskSpecT


@typing.runtime_checkable
class TaskExecutor(Protocol[TaskSpecT, TaskResultT]):
    @abstractmethod
    def execute(self, spec: TaskSpecT, model_executor: ModelExecutor) -> TaskResultT:
        raise NotImplementedError
