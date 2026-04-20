from atomforge.registry.core.registry import EntryPointRegistryBase
from atomforge.registry.model.helpers import manifest_to_registration
from atomforge.registry.model.manifest import ModelManifest


class ModelRegistry(EntryPointRegistryBase):
    entry_point_group = "atomforge.model"
    manifest_type = ModelManifest
    converter = staticmethod(manifest_to_registration)
    kind_label = "Model kind"

    def _register(self, registration, model_kind: str) -> None:
        super()._register(registration, model_kind)
