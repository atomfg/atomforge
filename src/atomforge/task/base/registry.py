from dataclasses import dataclass

from .executor import TaskExecutor
from .result import TaskResult
from .spec import TaskSpec


@dataclass(frozen=True)
class TaskRegistration:
    spec_model: type[TaskSpec]
    result_model: type[TaskResult]
    executor: TaskExecutor


class TaskRegistry:
    def __init__(self) -> None:
        self._registrations: dict[str, TaskRegistration] = {}

    def register(
        self,
        task_kind: str,
        spec_model: type[TaskSpec],
        result_model: type[TaskResult],
        executor: TaskExecutor,
    ) -> None:
        if task_kind in self._registrations:
            raise ValueError(f"Task kind already registered: {task_kind}")

        self._registrations[task_kind] = TaskRegistration(
            spec_model=spec_model,
            result_model=result_model,
            executor=executor,
        )

    def get(self, task_kind: str) -> TaskRegistration:
        try:
            return self._registrations[task_kind]
        except KeyError as exc:
            raise KeyError(f"Unknown task kind: {task_kind}") from exc
