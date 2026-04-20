import json
import inspect
import re
from importlib import import_module
from importlib.metadata import distribution

from atomforge.model.core.executor import ModelExecutor
from atomforge.model.core.metadata import ModelMetadata
from atomforge.model.core.property import Property
from atomforge.model.core.resource_caps import ResourceCapabilities
from atomforge.model.core.spec import ModelSpec
from atomforge.model.probes import ResourceProbe
from atomforge.registry.model.manifest import ModelManifest
from atomforge.registry.model.registration import ModelRegistration


def normalize_distribution_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def wrap_environment_factory(factory, provider_requirements: list[str]):
    def wrapped(spec):
        env = factory(spec)
        return env.with_provider_requirement(provider_requirements)

    return wrapped


class ModelRegistryError(ValueError):
    pass


class ManifestToRegistrationConverter:
    @staticmethod
    def _resolve_distribution(name: str) -> str:
        dist = distribution(name)
        text = dist.read_text("direct_url.json")
        if text is not None:
            data = json.loads(text)
            editable = data.get("dir_info", {}).get("editable", False)
            url = data.get("url")
        else:
            editable = False
            url = None

        if editable:
            return f"{name} @ {url}"
        return f"{dist.metadata['Name']}=={dist.version}"

    @staticmethod
    def _load_module(dotted_path: str):
        try:
            module_name, symbol_name = dotted_path.split(":", 1)
            module = import_module(module_name)
            return getattr(module, symbol_name)
        except (ImportError, AttributeError, ValueError) as exc:
            raise ModelRegistryError(
                f"Error loading module '{dotted_path}': {exc}"
            ) from exc

    def _load_model_spec(self, spec_str: str):
        model_spec = self._load_module(spec_str)
        if not issubclass(model_spec, ModelSpec):
            raise ModelRegistryError(
                f"Model spec '{spec_str}' must be a subclass of ModelSpec"
            )
        return model_spec

    def _load_executor(self, executor_str: str):
        executor_class = self._load_module(executor_str)
        if not issubclass(executor_class, ModelExecutor):
            raise ModelRegistryError(
                f"Executor class '{executor_str}' must be a subclass of ModelExecutor"
            )
        return executor_class

    def _load_supported_properties(self, properties_str: str) -> frozenset[Property]:
        supported_properties = self._load_module(properties_str)
        if not isinstance(supported_properties, frozenset) or not all(
            isinstance(prop, Property) for prop in supported_properties
        ):
            raise ModelRegistryError(
                f"Supported properties '{properties_str}' must be a frozenset of Property values"
            )
        return supported_properties

    def _load_environment_factory(self, factory_str: str):
        factory = self._load_module(factory_str)
        if not callable(factory):
            raise ModelRegistryError(
                f"Environment factory '{factory_str}' must be callable"
            )
        return factory

    def _load_metadata(self, metadata_str: str) -> ModelMetadata:
        metadata = self._load_module(metadata_str)
        if not isinstance(metadata, ModelMetadata):
            raise ModelRegistryError(
                f"Metadata '{metadata_str}' must be an instance of ModelMetadata"
            )
        return metadata

    def _load_resource_capabilities(
        self, capabilities_str: str
    ) -> ResourceCapabilities:
        resource_capabilities = self._load_module(capabilities_str)
        if not isinstance(resource_capabilities, ResourceCapabilities):
            raise ModelRegistryError(
                f"Resource capabilities '{capabilities_str}' must be an instance of ResourceCapabilities"
            )
        return resource_capabilities

    def _load_probe(self, probe_str: str | None) -> ResourceProbe | None:
        if probe_str is None:
            return None

        probe = self._load_module(probe_str)
        if inspect.isclass(probe) or not callable(probe):
            raise ModelRegistryError(f"Probe '{probe_str}' must be callable")
        return probe

    def _validate_distribution(
        self, manifest_distribution: list[str], entry_point_package: str
    ) -> None:
        if normalize_distribution_name(entry_point_package) not in {
            normalize_distribution_name(name) for name in manifest_distribution
        }:
            raise ModelRegistryError(
                f"Entry point package '{entry_point_package}' must be listed in the manifest's distribution field"
            )

    def convert(
        self, manifest: ModelManifest, entry_point_name: str, entry_point_package: str
    ) -> tuple[ModelRegistration, str]:
        model_spec = self._load_model_spec(manifest.model_spec)
        executor_class = self._load_executor(manifest.executor_class)
        supported_properties = self._load_supported_properties(
            manifest.supported_properties
        )
        environment_factory = self._load_environment_factory(manifest.environment_factory)
        metadata = self._load_metadata(manifest.metadata)
        resource_capabilities = self._load_resource_capabilities(
            manifest.resource_capabilities
        )
        probe = self._load_probe(manifest.probe)

        self._validate_distribution(manifest.distribution, entry_point_package)
        provider_requirements = [
            self._resolve_distribution(name) for name in manifest.distribution
        ]
        wrapped_environment_factory = wrap_environment_factory(
            environment_factory, provider_requirements
        )

        return ModelRegistration(
            model_spec=model_spec,
            metadata=metadata,
            executor_class=executor_class,
            supported_properties=supported_properties,
            environment_factory=wrapped_environment_factory,
            resource_capabilities=resource_capabilities,
            probe=probe,
        ), manifest.kind

    def __call__(
        self, manifest: ModelManifest, entry_point_name: str, entry_point_package: str
    ) -> tuple[ModelRegistration, str]:
        return self.convert(manifest, entry_point_name, entry_point_package)


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
