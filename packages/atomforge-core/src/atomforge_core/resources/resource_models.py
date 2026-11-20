from pydantic import BaseModel, ConfigDict, Field
from typing import Literal


class ExecutionResources(BaseModel):
    model_config = ConfigDict(extra="forbid")
    accelerator: Literal["default", "gpu", "cpu", "cuda", "rocm", "mps"] = Field(
        default="default",
        description=(
            "The accelerator to use: a backend (cpu, cuda, rocm, mps), 'gpu' for the "
            "first of cuda, rocm and mps that the model supports and the machine has, "
            "or 'default'."
        ),
    )
    precision: Literal["default", "f32", "f64"] = Field(
        default="default", description="The numerical precision to use for execution."
    )
    strict: bool = Field(
        default=False,
        description="Whether to strictly enforce the specified resources or allow downgrades if the requested resources are not available or a model does not support them.",
    )


class ResolvedResources(BaseModel):
    """
    ResolvedResources represents the realizable execution resources after resolving defaults and validating the specified resources.

    This means for example downgrading from gpu to cpu if gpu is not available.
    """

    model_config = ConfigDict(extra="forbid")
    accelerator: Literal["cpu", "cuda", "rocm", "mps"] | None = Field(
        description="The accelerator backend to use for execution."
    )
    precision: Literal["f32", "f64"] | None = Field(
        description="The numerical precision to use for execution."
    )
    messages: dict[str, str] = Field(
        default_factory=dict,
        description="Messages related to resource resolution, such as warnings about downgrades.",
    )
