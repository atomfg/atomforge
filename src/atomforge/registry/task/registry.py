from atomforge.registry.core.registry import EntryPointRegistryBase
from atomforge.registry.task.helpers import manifest_to_registration
from atomforge.registry.task.manifest import TaskManifest


class TaskRegistry(EntryPointRegistryBase):
    entry_point_group = "atomforge.task"
    manifest_type = TaskManifest
    converter = staticmethod(manifest_to_registration)
    kind_label = "Task kind"

    def _register(self, registration, task_kind: str) -> None:
        super()._register(registration, task_kind)


if __name__ == "__main__":
    from rich import print

    registry = TaskRegistry.default()

    for task_kind, registration in registry._registrations.items():
        print(registration)
