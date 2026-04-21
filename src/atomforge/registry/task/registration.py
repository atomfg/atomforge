from dataclasses import dataclass
from typing import Callable, Generic

from atomforge.env.base.env import EnvironmentSpec
from atomforge.task.core.capability import TaskCapabilitySpec
from atomforge.task.core.executor import TaskExecutor
from atomforge.task.core.result import TaskResultT
from atomforge.task.core.spec import TaskSpecT
from atomforge.env.base.factory import EnvironmentFactory


@dataclass(frozen=True)
class TaskRegistration(Generic[TaskSpecT, TaskResultT]):
    spec_model: type[TaskSpecT]
    result_model: type[TaskResultT]
    executor_class: type[TaskExecutor[TaskSpecT, TaskResultT]]
    capability_spec: TaskCapabilitySpec
    environment_factory: EnvironmentFactory[TaskSpecT]
