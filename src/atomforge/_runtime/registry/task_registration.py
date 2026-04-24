from dataclasses import dataclass
from typing import Generic

from atomforge._core.task.capability import TaskCapabilitySpec
from atomforge._core.task.executor import TaskExecutor
from atomforge._core.task.result import TaskResultT
from atomforge._core.task.spec import TaskSpecT
from atomforge._core.env.factory import EnvironmentFactory


@dataclass(frozen=True)
class TaskRegistration(Generic[TaskSpecT, TaskResultT]):
    spec_model: type[TaskSpecT]
    result_model: type[TaskResultT]
    executor_class: type[TaskExecutor[TaskSpecT, TaskResultT]]
    capability_spec: TaskCapabilitySpec
    environment_factory: EnvironmentFactory[TaskSpecT]
