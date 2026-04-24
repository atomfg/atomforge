from pydantic import BaseModel, ConfigDict, Field, field_validator


class RegistryManifestBase(BaseModel):
    model_config = ConfigDict(frozen=True)

    distribution: list[str] | str = Field(
        default_factory=list,
        description="The distribution(s) that provide the registry entry point.",
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


def ensure_dotted_path(value):
    if isinstance(value, str) and ":" in value:
        return value
    raise TypeError(
        "Value must be a dotted path in the format 'module.submodule:SymbolName'"
    )
