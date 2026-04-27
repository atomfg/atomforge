from atomforge_runtime.registry.base_converter import ManifestToRegistrationConverterBase
from atomforge_core.registry.errors import RegistryCoreError
from atomforge_core.registry.task_manifest import TaskManifest
from atomforge_runtime.registry.task_registration import TaskRegistration
from atomforge_core.task.spec import TaskSpec


class TaskRegistryError(RegistryCoreError):
    pass


class ManifestToRegistrationConverter(ManifestToRegistrationConverterBase):
    error_class = TaskRegistryError

    def _load_components(self, manifest: TaskManifest) -> dict[str, object]:
        return {
            "spec_model": self._load_subclass(
                manifest.spec_model, TaskSpec, "Spec model"
            ),
            "executor_cls": manifest.executor_cls,
            "result_model": manifest.result_model,
            "capability_spec": manifest.capability_spec,
            "environment_factory_cls": manifest.environment_factory_cls,
        }

    def _build_registration(
        self,
        manifest: TaskManifest,
        components: dict[str, object],
    ) -> TaskRegistration:
        return TaskRegistration(
            kind=manifest.kind,
            spec_model=components["spec_model"],
            executor_class_path=components["executor_cls"],
            result_model_path=components["result_model"],
            capability_spec_path=components["capability_spec"],
            environment_factory_path=components["environment_factory_cls"],
            source=manifest.distribution,
        )


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
