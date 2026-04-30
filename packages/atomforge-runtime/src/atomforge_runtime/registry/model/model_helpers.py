from atomforge_runtime.registry.base_converter import ManifestToRegistrationConverterBase
from atomforge_core.registry.errors import RegistryCoreError
from atomforge_core.model.spec import ModelSpec
from atomforge_core.registry.model_manifest import ModelManifest
from atomforge_runtime.registry.model.model_registration import ModelRegistration


class ModelRegistryError(RegistryCoreError):
    pass


class ManifestToRegistrationConverter(ManifestToRegistrationConverterBase):
    error_class = ModelRegistryError

    def _load_components(self, manifest: ModelManifest) -> dict[str, object]:
        return {
            "model_spec": self._load_subclass(
                manifest.model_spec, ModelSpec, "Model spec"
            ),
            "executor_cls": manifest.executor_cls,
            "supported_properties": manifest.supported_properties,
            "environment_factory_cls": manifest.environment_factory_cls,
            "metadata": manifest.metadata,
            "resource_capabilities": manifest.resource_capabilities,
            "probe": manifest.probe,
            "task_overrides": manifest.task_overrides,
        }

    def _build_registration(
        self,
        manifest: ModelManifest,
        components: dict[str, object],
    ) -> ModelRegistration:
        return ModelRegistration(
            kind=manifest.kind,
            model_spec=components["model_spec"],
            metadata_path=components["metadata"],
            executor_class_path=components["executor_cls"],
            supported_properties_path=components["supported_properties"],
            environment_factory_path=components["environment_factory_cls"],
            resource_capabilities_path=components["resource_capabilities"],
            probe_path=components["probe"],
            task_overrides=components["task_overrides"],
            source=manifest.distribution,
        )


def manifest_to_registration(
    manifest: ModelManifest, entry_point_name: str, entry_point_package: str
) -> tuple[ModelRegistration, str]:
    try:
        converter = ManifestToRegistrationConverter()
        return converter(manifest, entry_point_name, entry_point_package)
    except ModelRegistryError as exc:
        raise ModelRegistryError(
            f"Error registering '{entry_point_name}' from '{entry_point_package}': {exc}"
        ) from exc
    except Exception as exc:
        raise ModelRegistryError(
            f"Unexpected error registering '{entry_point_name}' from '{entry_point_package}': {exc}"
        ) from exc
