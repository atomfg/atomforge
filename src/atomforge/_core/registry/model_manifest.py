from pydantic import Field, field_validator

from atomforge._core.registry.base_manifest import RegistryManifestBase, ensure_dotted_path


class ModelManifest(RegistryManifestBase):
    kind: str = Field(description="Unique identifier for the model kind")
    model_spec: str = Field(
        description="The model spec class, as a dotted path like 'my_package.my_module:MyModelSpec'"
    )
    executor_cls: str = Field(
        description="The model executor class, as a dotted path like 'my_package.my_module:MyModelExecutor'"
    )
    supported_properties: str = Field(
        description="The model supported properties object, as a dotted path like 'my_package.my_module:MySupportedProperties'"
    )
    environment_factory_cls: str = Field(
        description="The environment factory class, as a dotted path like 'my_package.my_module:MyEnvironmentFactory'"
    )
    metadata: str = Field(
        description="The model metadata object, as a dotted path like 'my_package.my_module:MyMetadata'"
    )
    resource_capabilities: str = Field(
        description="The model resource capabilities object, as a dotted path like 'my_package.my_module:MyResourceCapabilities'"
    )
    distribution: list[str] | str = Field(
        default_factory=list,
        description="The distribution(s) that provide the model entry point.",
    )
    probe: str | None = Field(
        default=None,
        description="Optional dotted path to a resource probe callable.",
    )

    @field_validator(
        "model_spec",
        "executor_cls",
        "supported_properties",
        "environment_factory_cls",
        "metadata",
        "resource_capabilities",
        mode="before",
    )
    @classmethod
    def ensure_dotted_path(cls, value):
        return ensure_dotted_path(value)

    @field_validator("probe", mode="before")
    @classmethod
    def ensure_probe_path(cls, value):
        if value is None:
            return value
        return ensure_dotted_path(value)
