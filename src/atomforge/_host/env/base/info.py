from __future__ import annotations

from pathlib import Path
from typing import Mapping

from pydantic import BaseModel, Field, ConfigDict
from atomforge._host.env.base.handle import EnvironmentHandle


class EnvironmentInfo(BaseModel):
    model_config = ConfigDict(frozen=True)
    handle: EnvironmentHandle
    path: Path | None
    python_executable: Path | None
    metadata: Mapping[str, str] = Field(default_factory=dict)

    @property
    def exists(self) -> bool:
        return (
            self.path is not None
            and self.path.exists()
            and self.python_executable is not None
            and self.python_executable.exists()
        )
