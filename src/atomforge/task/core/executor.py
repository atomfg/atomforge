from abc import abstractmethod
from typing import Protocol, TypeVar
import typing

from atomforge.model.core.executor import ModelExecutor

from atomforge.task.core.result import TaskResultT
from atomforge.task.core.spec import TaskSpecT



@typing.runtime_checkable
class TaskExecutor(Protocol[TaskSpecT, TaskResultT]):
    @abstractmethod
    def execute(self, spec: TaskSpecT, model_executor: ModelExecutor) -> TaskResultT:
        raise NotImplementedError
