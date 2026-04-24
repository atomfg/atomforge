from pydantic import BaseModel, ConfigDict, Field
from typing import Callable, Literal

from atomforge._core.model.spec import ModelSpecT

Accelerator = Literal["cpu", "gpu", "mps"]


class ProbeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    available_accelerators: frozenset[Accelerator] = Field(
        default_factory=lambda: frozenset({"cpu"})
    )
    reasons: dict[Accelerator, str] = Field(default_factory=dict)


ResourceProbe = Callable[[ModelSpecT], ProbeResult]