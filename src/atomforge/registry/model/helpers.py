from atomforge.registry.core.converter import ManifestToRegistrationConverterBase
from atomforge.registry.core.errors import RegistryCoreError
from atomforge.registry.core.helpers import resolve_distribution
from atomforge.model.core.executor import ModelExecutor
from atomforge.model.core.metadata import ModelMetadata
from atomforge.model.core.property import Property
from atomforge.model.core.resource_caps import ResourceCapabilities
from atomforge.model.core.spec import ModelSpec
from atomforge.model.probes import ResourceProbe
from atomforge.registry.model.manifest import ModelManifest
from atomforge.registry.model.registration import ModelRegistration
from atomforge.env.base.factory import EnvironmentFactory

class ModelRegistryError(RegistryCoreError):
    pass


class ManifestToRegistrationConverter(ManifestToRegistrationConverterBase):
    error_class = ModelRegistryError

    def _load_supported_properties(self, properties_str: str) -> frozenset[Property]:
        supported_properties = self._load_symbol(properties_str)
        if not isinstance(supported_properties, frozenset) or not all(
            isinstance(prop, Property) for prop in supported_properties
        ):
            self._raise(
                f"Supported properties '{properties_str}' must be a frozenset of Property values"
            )
        return supported_properties

    def _load_components(self, manifest: ModelManifest) -> dict[str, object]:
        return {
            "model_spec": self._load_subclass(
                manifest.model_spec, ModelSpec, "Model spec"
            ),
            "executor_cls": self._load_subclass(
                manifest.executor_cls, ModelExecutor, "Executor class"
            ),
            "supported_properties": self._load_supported_properties(
                manifest.supported_properties
            ),
            "environment_factory_cls": self._load_subclass(
                manifest.environment_factory_cls, EnvironmentFactory, "Environment factory"
            ),
            "metadata": self._load_instance(
                manifest.metadata, ModelMetadata, "Metadata"
            ),
            "resource_capabilities": self._load_instance(
                manifest.resource_capabilities,
                ResourceCapabilities,
                "Resource capabilities",
            ),
            "probe": (
                None
                if manifest.probe is None
                else self._load_callable(
                    manifest.probe, "Probe", reject_classes=True
                )
            ),
        }

    def _build_registration(
        self, manifest: ModelManifest, components: dict[str, object], environment_factory: EnvironmentFactory
    ) -> ModelRegistration:
        return ModelRegistration(
            model_spec=components["model_spec"],
            metadata=components["metadata"],
            executor_class=components["executor_cls"],
            supported_properties=components["supported_properties"],
            environment_factory=environment_factory,
            resource_capabilities=components["resource_capabilities"],
            probe=components["probe"],
            source=manifest.distribution
        )

    @staticmethod
    def _resolve_distribution(name: str) -> str:
        return resolve_distribution(name)


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
