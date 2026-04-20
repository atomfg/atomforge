from atomforge.registry.task.manifest import TaskManifest
from atomforge.registry.task.registration import TaskRegistration

from atomforge.task.core.spec import TaskSpec
from atomforge.task.core.result import TaskResult
from atomforge.task.core.executor import TaskExecutor
from atomforge.task.core.capability import TaskCapabilitySpec

from importlib import import_module
from importlib.metadata import distribution
import json

import re


def normalize_distribution_name(name: str) -> str:
    """
    Normalize a distribution name using PEP 503 semantics:
    lowercase, and collapse runs of '-', '_' and '.' to '-'.
    """
    return re.sub(r"[-_.]+", "-", name).lower()


def wrap_environment_factory(factory, provider_requirements: list[str]):
    def wrapped(spec):
        env = factory(spec)
        return env.with_provider_requirement(provider_requirements)

    return wrapped


class TaskRegistryError(ValueError):
    pass


class ManifestToRegistrationConverter:
    @staticmethod
    def _resolve_distribution(name: str) -> str:
        """
        Resolve a distribution name to a pip install string, handling editable installs if necessary.

        For editable installs, this assumes that the distribution is installed in a way
        that provides metadata according to PEP 610. This means that the distribution
        should have a "direct_url.json" file in its metadata that specifies the source of the editable install.
        If it does not, it will not be considered an editable installation and EnvironmentProviders
        will assume it's safe to install from PyPI / package registries. This is a reasonable assumption for most cases,
        but may not be correct in all cases.
        """

        dist = distribution(name)
        text = dist.read_text("direct_url.json")
        if text is not None:
            data = json.loads(text)
            editable = data.get("dir_info", {}).get("editable", False)
            url = data.get("url")
        else:
            editable = False
            url = None

        # Return the pip install string for the distribution
        if editable:
            return f"{name} @ {url}"
        else:
            return f"{dist.metadata['Name']}=={dist.version}"

    @staticmethod
    def _load_module(dotted_path: str):
        try:
            module_name, class_name = dotted_path.split(":", 1)
            module = import_module(module_name)
            return getattr(module, class_name)
        except (ImportError, AttributeError, ValueError) as e:
            raise TaskRegistryError(f"Error loading module '{dotted_path}': {e}") from e

    def _load_spec(self, spec_str: str) -> type[TaskSpec]:
        spec_model = self._load_module(spec_str)
        if not issubclass(spec_model, TaskSpec):
            raise TaskRegistryError(
                f"Spec model '{spec_str}' must be a subclass of TaskSpec"
            )

        return spec_model

    def _load_result(self, result_str: str) -> type[TaskResult]:
        result_model = self._load_module(result_str)
        if not issubclass(result_model, TaskResult):
            raise TaskRegistryError(
                f"Result model '{result_str}' must be a subclass of TaskResult"
            )
        return result_model

    def _load_executor(self, executor_str: str) -> type[TaskExecutor]:
        executor_class = self._load_module(executor_str)
        if not issubclass(executor_class, TaskExecutor):
            raise TaskRegistryError(
                f"Executor class '{executor_str}' must be a subclass of TaskExecutor"
            )
        return executor_class

    def _load_capability_spec(self, capability_spec_str: str) -> TaskCapabilitySpec:
        capability_spec = self._load_module(capability_spec_str)
        if not isinstance(capability_spec, TaskCapabilitySpec):
            raise TaskRegistryError(
                f"Capability spec '{capability_spec_str}' must be an instance of TaskCapabilitySpec"
            )
        return capability_spec

    def _load_environment_factory(self, factory_str: str):
        factory = self._load_module(factory_str)
        if not callable(factory):
            raise TaskRegistryError(
                f"Environment factory '{factory_str}' must be callable"
            )
        return factory
    
    def _validate_distribution(self, manifest_distribution: list[str], entry_point_package: str):
        if normalize_distribution_name(entry_point_package) not in map(normalize_distribution_name, manifest_distribution):
            raise TaskRegistryError(
                f"Entry point package '{entry_point_package}' must be listed in the manifest's distribution field"
            )

    def convert(
        self, manifest: TaskManifest, entry_point_name: str, entry_point_package: str
    ) -> tuple[TaskRegistration, str]:
        spec_model = self._load_spec(manifest.spec_model)
        executor_class = self._load_executor(manifest.executor_class)
        result_model = self._load_result(manifest.result_model)
        capability_spec = self._load_capability_spec(manifest.capability_spec)
        org_environment_factory = self._load_environment_factory(
            manifest.environment_factory
        )

        self._validate_distribution(manifest.distribution, entry_point_package)

        provider_requirements = [
            self._resolve_distribution(d) for d in manifest.distribution
        ]

        environment_factory = wrap_environment_factory(
            org_environment_factory, provider_requirements
        )

        return TaskRegistration(
            spec_model=spec_model,
            executor_class=executor_class,
            result_model=result_model,
            capability_spec=capability_spec,
            environment_factory=environment_factory,
        ), manifest.kind

    def __call__(self, manifest: TaskManifest, entry_point_name: str, entry_point_package: str) -> tuple[TaskRegistration, str]:
        return self.convert(manifest, entry_point_name, entry_point_package)


def manifest_to_registration(
    manifest: TaskManifest, entry_point_name: str, entry_point_package: str
) -> tuple[TaskRegistration, str]:

    try:
        converter = ManifestToRegistrationConverter()
        return converter(manifest, entry_point_name, entry_point_package)
    except TaskRegistryError as e:
        raise TaskRegistryError(
            f"Error registering '{entry_point_name}' from '{entry_point_package}': {e}"
        ) from e
    except Exception as e:
        raise TaskRegistryError(
            f"Unexpected error registering '{entry_point_name}' from '{entry_point_package}': {e}"
        ) from e
