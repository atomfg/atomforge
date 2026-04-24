from atomforge._core.env.factory import EnvironmentFactory
from atomforge._runtime.registry.base_converter import ManifestToRegistrationConverterBase
from atomforge._core.registry.errors import RegistryCoreError
from atomforge._runtime.registry.helpers import resolve_distribution
from atomforge._core.registry.task_manifest import TaskManifest
from atomforge._runtime.registry.task_registration import TaskRegistration
from atomforge._core.task.capability import TaskCapabilitySpec
from atomforge._core.task.executor import TaskExecutor
from atomforge._core.task.result import TaskResult
from atomforge._core.task.spec import TaskSpec


class TaskRegistryError(RegistryCoreError):
    pass


class ManifestToRegistrationConverter(ManifestToRegistrationConverterBase):
    error_class = TaskRegistryError

    def _load_components(self, manifest: TaskManifest) -> dict[str, object]:
        return {
            "spec_model": self._load_subclass(
                manifest.spec_model, TaskSpec, "Spec model"
            ),
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
                manifest.environment_factory_cls,
                EnvironmentFactory,
                "Environment factory",
            ),
        }

    def _build_registration(
        self,
        manifest: TaskManifest,
        components: dict[str, object],
        environment_factory: EnvironmentFactory,
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
