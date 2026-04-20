from pydantic import BaseModel, ConfigDict, Field, field_validator


class TaskManifest(BaseModel):
    model_config = ConfigDict(frozen=True)
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
    distribution: list[str] | str = Field(
        default_factory=list, description="The distribution(s) for the task"
    )

    @field_validator("distribution", mode="before")
    @classmethod
    def ensure_distribution_list(cls, v):
        if isinstance(v, str):
            return [v]
        elif (
            isinstance(v, list)
            and all(isinstance(item, str) for item in v)
            and len(v) > 0
        ):
            return v
        else:
            raise TypeError(
                "distribution must be a non-empty list of strings or a single string"
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
    def ensure_dotted_path(cls, v):
        if isinstance(v, str) and ":" in v:
            return v
        else:
            raise TypeError(
                "Value must be a dotted path in the format 'module.submodule:ClassName' or 'module.submodule:function_name'"
            )
