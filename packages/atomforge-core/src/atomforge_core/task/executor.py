from abc import abstractmethod
from dataclasses import dataclass
from typing import Protocol
import typing

from atomforge_core.model.executor import ModelExecutor
from atomforge_core.resources.resource_models import ResolvedResources
from atomforge_core.task.executability import CompatibilityCheck

from atomforge_core.task.result import TaskResultT
from atomforge_core.task.spec import TaskSpecT


@dataclass(frozen=True)
class TaskExecutionContext:
    model_executor: ModelExecutor | None = None
    resolved_resources: ResolvedResources | None = None


def require_model_executor(
    context: TaskExecutionContext, *, task_kind: str
) -> ModelExecutor:
    if context.model_executor is None:
        raise ValueError(
            f"Task of kind {task_kind} requires a model executor, but none was provided"
        )
    return context.model_executor


@typing.runtime_checkable
class TaskExecutor(Protocol[TaskSpecT, TaskResultT]):
    @classmethod
    def check_compatibility(
        cls,
        spec: TaskSpecT,
        context: TaskExecutionContext,
    ) -> CompatibilityCheck:
        return CompatibilityCheck(ok=True)

    @abstractmethod
    def execute(self, spec: TaskSpecT, context: TaskExecutionContext) -> TaskResultT:
        raise NotImplementedError
