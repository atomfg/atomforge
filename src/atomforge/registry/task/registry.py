from typing import Self

from atomforge.registry.task.helpers import manifest_to_registration
from atomforge.registry.task.manifest import TaskManifest
from atomforge.registry.task.registration import (
    TaskRegistration,
)


class TaskRegistry:
    def __init__(self) -> None:
        self._registrations: dict[str, TaskRegistration] = {}

    def _register(
        self,
        registration: TaskRegistration,
        task_kind: str,
    ) -> None:
        if task_kind in self._registrations:
            raise ValueError(f"Task kind already registered: {task_kind}")

        self._registrations[task_kind] = registration

    def get(self, task_kind: str) -> TaskRegistration:
        try:
            return self._registrations[task_kind]
        except KeyError as exc:
            raise KeyError(f"Unknown task kind: {task_kind}") from exc

    def _load_entry_points(self) -> None:
        from importlib.metadata import entry_points

        eps = entry_points(group="atomforge.task")
        entry_point_packages = {}

        for ep in eps:
            manifest = ep.load()

            if not isinstance(manifest, TaskManifest):
                raise TypeError(
                    f"Entry point '{ep.name}' must be a TaskManifest instance"
                )

            registration, kind = manifest_to_registration(
                manifest, entry_point_name=ep.name, entry_point_package=ep.dist.name
            )

            if kind in self._registrations:
                raise ValueError(
                    f"Task kind already registered: {ep.name} (from {ep.dist.name} and {entry_point_packages[kind]})"
                )

            self._register(registration, kind)
            entry_point_packages[kind] = ep.dist.name

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
