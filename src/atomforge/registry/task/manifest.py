from pydantic import Field, field_validator

from atomforge.registry.core.manifest import RegistryManifestBase, ensure_dotted_path


class TaskManifest(RegistryManifestBase):
    kind: str = Field(description="Unique identifier for the task kind")
    spec_model: str = Field(
        description="The specification model for the task, as a dotted path to a class, e.g. 'my_package.my_module:MySpecModel'"
    )
    executor_class: str = Field(
        description="The executor class for the task, as a dotted path to a class, e.g. 'my_package.my_module:MyTaskExecutor'"
    )
    result_model: str = Field(
        description="The result model for the task, as a dotted path to a class, e.g. 'my_package.my_module:MyResultModel'"
    )
    capability_spec: str = Field(
        description="The capability specification for the task, as a dotted path to a class, e.g. 'my_package.my_module:MyCapabilitySpec'"
    )
    environment_factory: str = Field(
        description="The environment factory for the task, as a dotted path to a function, e.g. 'my_package.my_module:my_environment_factory'"
    )

    @field_validator(
        "spec_model",
        "executor_class",
        "result_model",
        "capability_spec",
        "environment_factory",
        mode="before",
    )
    @classmethod
    def ensure_dotted_path(cls, value):
        return ensure_dotted_path(value)
