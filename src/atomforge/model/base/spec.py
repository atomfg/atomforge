from pydantic import BaseModel, ConfigDict
from typing import TypeVar, Callable

from atomforge.env.base.env import EnvironmentSpec


class ModelSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


ModelSpecT = TypeVar("SpecT", bound=ModelSpec)

EnvironmentFactory= Callable[[ModelSpecT], EnvironmentSpec]