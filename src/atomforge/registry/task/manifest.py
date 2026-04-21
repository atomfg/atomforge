from pydantic import Field, field_validator

from atomforge.registry.core.manifest import RegistryManifestBase, ensure_dotted_path


class TaskManifest(RegistryManifestBase):
    kind: str = Field(description="Unique identifier for the task kind")
    spec_model: str = Field(
        description="The specification model for the task, as a dotted path to a class, e.g. 'my_package.my_module:MySpecModel'"
    )
    executor_cls: str = Field(
        description="The executor class for the task, as a dotted path to a class, e.g. 'my_package.my_module:MyTaskExecutor'"
    )
    result_model: str = Field(
        description="The result model for the task, as a dotted path to a class, e.g. 'my_package.my_module:MyResultModel'"
    )
    capability_spec: str = Field(
        description="The capability specification for the task, as a dotted path to a class, e.g. 'my_package.my_module:MyCapabilitySpec'"
    )
    environment_factory_cls: str = Field(
        description="The environment factory class for the task, as a dotted path to a class, e.g. 'my_package.my_module:MyEnvironmentFactory'"
    )

    @field_validator(
        "spec_model",
        "executor_cls",
        "result_model",
        "capability_spec",
        "environment_factory_cls",
        mode="before",
    )
    @classmethod
    def ensure_dotted_path(cls, value):
        return ensure_dotted_path(value)
