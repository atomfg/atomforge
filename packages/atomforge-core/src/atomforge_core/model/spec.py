from typing import Any, TypeVar

from pydantic import BaseModel, ConfigDict


class ModelSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    environment_profile: str = "tested"

    def scientific_payload(self, *, mode: str = "python") -> dict[str, Any]:
        """Return model settings excluding environment realization choices."""
        return self.model_dump(mode=mode, exclude={"environment_profile"})


ModelSpecT = TypeVar("SpecT", bound=ModelSpec)
