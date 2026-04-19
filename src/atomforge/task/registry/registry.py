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


class TaskRegistry:
    def __init__(self) -> None:
        self._registrations: dict[str, TaskRegistration] = {}

    def register(
        self,
        task_kind: str,
        spec_model: type[TaskSpecT],
        result_model: type[TaskResultT],
        executor_class: type[TaskExecutor[TaskSpecT, TaskResultT]],
        capability_spec: TaskCapabilitySpec,
        environment_factory: Callable[[TaskSpecT], EnvironmentSpec],
    ) -> None:
        if task_kind in self._registrations:
            raise ValueError(f"Task kind already registered: {task_kind}")

        self._registrations[task_kind] = TaskRegistration(
            spec_model=spec_model,
            result_model=result_model,
            executor_class=executor_class,
            capability_spec=capability_spec,
            environment_factory=environment_factory,
        )

    def get(self, task_kind: str) -> TaskRegistration:
        try:
            return self._registrations[task_kind]
        except KeyError as exc:
            raise KeyError(f"Unknown task kind: {task_kind}") from exc
