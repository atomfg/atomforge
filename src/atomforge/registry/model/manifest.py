from pydantic import BaseModel, ConfigDict, Field, field_validator


class ModelManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: str = Field(description="Unique identifier for the model kind")
    model_spec: str = Field(
        description="The model spec class, as a dotted path like 'my_package.my_module:MyModelSpec'"
    )
    executor_class: str = Field(
        description="The model executor class, as a dotted path like 'my_package.my_module:MyModelExecutor'"
    )
    supported_properties: str = Field(
        description="The model supported properties object, as a dotted path like 'my_package.my_module:MySupportedProperties'"
    )
    environment_factory: str = Field(
        description="The environment factory, as a dotted path like 'my_package.my_module:my_environment_factory'"
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

    @field_validator("distribution", mode="before")
    @classmethod
    def ensure_distribution_list(cls, value):
        if isinstance(value, str):
            return [value]
        if (
            isinstance(value, list)
            and all(isinstance(item, str) for item in value)
            and len(value) > 0
        ):
            return value
        raise TypeError(
            "distribution must be a non-empty list of strings or a single string"
        )

    @field_validator(
        "model_spec",
        "executor_class",
        "supported_properties",
        "environment_factory",
        "metadata",
        "resource_capabilities",
        mode="before",
    )
    @classmethod
    def ensure_dotted_path(cls, value):
        if isinstance(value, str) and ":" in value:
            return value
        raise TypeError(
            "Value must be a dotted path in the format 'module.submodule:SymbolName'"
        )

    @field_validator("probe", mode="before")
    @classmethod
    def ensure_probe_path(cls, value):
        if value is None:
            return value
        if isinstance(value, str) and ":" in value:
            return value
        raise TypeError(
            "Probe must be None or a dotted path in the format 'module.submodule:SymbolName'"
        )
