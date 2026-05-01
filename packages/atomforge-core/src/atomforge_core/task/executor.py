from abc import abstractmethod
from typing import Protocol
import typing

from atomforge_core.model.executor import ModelExecutor
from atomforge_core.task.executability import CompatibilityCheck

from atomforge_core.task.result import TaskResultT
from atomforge_core.task.spec import TaskSpecT


@typing.runtime_checkable
class TaskExecutor(Protocol[TaskSpecT, TaskResultT]):
    @classmethod
    def check_compatibility(
        cls,
        spec: TaskSpecT,
        model_executor: ModelExecutor,
    ) -> CompatibilityCheck:
        return CompatibilityCheck(ok=True)

    @abstractmethod
    def execute(self, spec: TaskSpecT, model_executor: ModelExecutor) -> TaskResultT:
        raise NotImplementedError
