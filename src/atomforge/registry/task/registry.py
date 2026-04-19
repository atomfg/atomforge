from dataclasses import dataclass
from typing import Callable, Generic, Self, TypeVar

from atomforge.env.base.env import EnvironmentSpec

from atomforge.task.core.capability import TaskCapabilitySpec
from atomforge.task.core.executor import TaskExecutor
from atomforge.task.core.result import TaskResult
from atomforge.task.core.spec import TaskSpec
from atomforge.registry.task.manifest import TaskManifest


TaskSpecT = TypeVar("TaskSpecT", bound=TaskSpec)
TaskResultT = TypeVar("TaskResultT", bound=TaskResult)

@dataclass(frozen=True)
class TaskRegistration(Generic[TaskSpecT, TaskResultT]):
    spec_model: type[TaskSpecT]
    result_model: type[TaskResultT]
    executor_class: type[TaskExecutor[TaskSpecT, TaskResultT]]
    capability_spec: TaskCapabilitySpec
    environment_factory: Callable[[TaskSpecT], EnvironmentSpec]


def load_module(dotted_path: str):
    from importlib import import_module

    module_name, class_name = dotted_path.split(":", 1)
    module = import_module(module_name)
    return getattr(module, class_name)

def manifest_to_registration(manifest: TaskManifest) -> TaskRegistration:
    spec_model = load_module(manifest.spec_model)
    executor_class = load_module(manifest.executor_class)
    result_model = load_module(manifest.result_model)
    capability_spec = load_module(manifest.capability_spec)
    environment_factory = load_module(manifest.environment_factory)
    return TaskRegistration(
        spec_model=spec_model,
        executor_class=executor_class,
        result_model=result_model,
        capability_spec=capability_spec,
        environment_factory=environment_factory,
    ), manifest.kind

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

    def _load_entry_points(self) -> None:
        from importlib.metadata import entry_points

        eps = entry_points(group="atomforge.task")

        for ep in eps:
            manifest = ep.load()
            registration, kind = manifest_to_registration(manifest)

            if kind in self._registrations:
                raise ValueError(f"Task kind already registered: {ep.name}")

            self._registrations[kind] = registration

    @classmethod
    def default(cls) -> Self:
        instance = cls()
        instance._load_entry_points()
        return instance


if __name__ == "__main__":
    from rich import print

    registry = TaskRegistry.default()

    for task_kind, registration in registry._registrations.items():
        print(registration)

