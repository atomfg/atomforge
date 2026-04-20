from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from atomforge.env.base.env import EnvironmentSpec
from atomforge.task.core.capability import TaskCapabilitySpec
from atomforge.task.core.executor import TaskExecutor
from atomforge.task.core.result import TaskResult
from atomforge.task.core.spec import TaskSpec

TaskSpecT = TypeVar("TaskSpecT", bound=TaskSpec)
TaskResultT = TypeVar("TaskResultT", bound=TaskResult)


@dataclass(frozen=True)
class TaskRegistration(Generic[TaskSpecT, TaskResultT]):
    spec_model: type[TaskSpecT]
    result_model: type[TaskResultT]
    executor_class: type[TaskExecutor[TaskSpecT, TaskResultT]]
    capability_spec: TaskCapabilitySpec
    environment_factory: Callable[[TaskSpecT], EnvironmentSpec]
