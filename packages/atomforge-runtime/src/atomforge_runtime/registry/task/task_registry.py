from atomforge_runtime.registry.registry import EntryPointRegistryBase
from atomforge_runtime.registry.task.task_helpers import manifest_to_registration
from atomforge_core.registry.task_manifest import TaskManifest


class TaskRegistry(EntryPointRegistryBase):
    entry_point_group = "atomforge.task"
    manifest_type = TaskManifest
    converter = staticmethod(manifest_to_registration)
    kind_label = "Task kind"

    def _register(self, registration, task_kind: str) -> None:
        super()._register(registration, task_kind)
