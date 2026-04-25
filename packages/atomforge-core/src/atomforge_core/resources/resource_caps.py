from pydantic import BaseModel, ConfigDict, Field
from typing import Literal


class ResourceCapabilities(BaseModel):
    """
    ResourceCapabilities represents which knobs of ExecutionResources a model supports.
    This is used for validating requested resources and for resolving defaults.

    If a field is None, it means that the model does not meaningfully use the corresponding resource.
    For example, if precision is None it means that the model cannot take advantage of higher/lower
    precision and will perform the same regardless of the precision specified in ExecutionResources.
    """

    model_config = ConfigDict(extra="forbid")
    accelerator: list[Literal["cpu", "gpu", "mps"]] | None = Field(
        default=None,
        description="The types of hardware accelerators supported by the model.",
    )
    precision: list[Literal["f32", "f64"]] | None = Field(
        default=None,
        description="The numerical precisions supported by the model.",
    )
