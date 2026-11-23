from atomforge_runtime.registry.registry import EntryPointRegistryBase
from atomforge_runtime.registry.model.model_helpers import manifest_to_registration
from atomforge_core.model.spec import ModelSpec
from atomforge_core.registry.model_manifest import ModelManifest


class ModelRegistry(EntryPointRegistryBase):
    entry_point_group = "atomforge.model"
    manifest_type = ModelManifest
    converter = staticmethod(manifest_to_registration)
    kind_label = "Model kind"

    def _register(self, registration, model_kind: str) -> None:
        super()._register(registration, model_kind)

    def variant(self, variant_id: str) -> ModelSpec:
        """The spec of a variant, with default settings, from its id
        ``<kind>/<variant_name>``."""
        kind, separator, name = variant_id.partition("/")
        registration = self.get(kind)
        if not separator:
            raise KeyError(
                f"'{variant_id}' is not a variant id; expected '<kind>/<variant>'"
            )
        variants = registration.model_spec.variants()
        for spec in variants:
            if spec.variant_name == name:
                return spec
        known = ", ".join(spec.variant_name for spec in variants)
        raise KeyError(f"Unknown variant of {kind}: {name} (known: {known})")
