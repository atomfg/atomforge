from pydantic import BaseModel, ConfigDict
from typing import TypeVar


class ModelSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


ModelSpecT = TypeVar("SpecT", bound=ModelSpec)
