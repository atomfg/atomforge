from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

class EnvironmentHandle(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    name: str
    provider: str
    path: Path
