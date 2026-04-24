from atomforge._runtime.registry.registry import EntryPointRegistryBase
from atomforge._runtime.registry.task.task_helpers import manifest_to_registration
from atomforge._core.registry.task_manifest import TaskManifest


class TaskRegistry(EntryPointRegistryBase):
    entry_point_group = "atomforge.task"
    manifest_type = TaskManifest
    converter = staticmethod(manifest_to_registration)
    kind_label = "Task kind"

    def _register(self, registration, task_kind: str) -> None:
        super()._register(registration, task_kind)
