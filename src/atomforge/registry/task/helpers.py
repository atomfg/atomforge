from atomforge.env.base.factory import EnvironmentFactory
from atomforge.registry.core.converter import ManifestToRegistrationConverterBase
from atomforge.registry.core.errors import RegistryCoreError
from atomforge.registry.core.helpers import resolve_distribution
from atomforge.registry.task.manifest import TaskManifest
from atomforge.registry.task.registration import TaskRegistration
from atomforge.task.core.capability import TaskCapabilitySpec
from atomforge.task.core.executor import TaskExecutor
from atomforge.task.core.result import TaskResult
from atomforge.task.core.spec import TaskSpec


class TaskRegistryError(RegistryCoreError):
    pass


class ManifestToRegistrationConverter(ManifestToRegistrationConverterBase):
    error_class = TaskRegistryError

    def _load_components(self, manifest: TaskManifest) -> dict[str, object]:
        return {
            "spec_model": self._load_subclass(manifest.spec_model, TaskSpec, "Spec model"),
            "executor_cls": self._load_subclass(
                manifest.executor_cls, TaskExecutor, "Executor class"
            ),
            "result_model": self._load_subclass(
                manifest.result_model, TaskResult, "Result model"
            ),
            "capability_spec": self._load_instance(
                manifest.capability_spec, TaskCapabilitySpec, "Capability spec"
            ),
            "environment_factory_cls": self._load_subclass(
                manifest.environment_factory_cls, EnvironmentFactory, "Environment factory"
            ),
        }

    def _build_registration(
        self, manifest: TaskManifest, components: dict[str, object], environment_factory: EnvironmentFactory
    ) -> TaskRegistration:
        return TaskRegistration(
            spec_model=components["spec_model"],
            executor_class=components["executor_cls"],
            result_model=components["result_model"],
            capability_spec=components["capability_spec"],
            environment_factory=environment_factory,
        )

    @staticmethod
    def _resolve_distribution(name: str) -> str:
        return resolve_distribution(name)


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
