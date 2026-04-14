from __future__ import annotations

from pathlib import Path
from typing import Mapping

from pydantic import BaseModel, Field, ConfigDict


class EnvironmentSpec(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    python: str | None = None
    requirements: tuple[str, ...] = ()
    channels: tuple[str, ...] = ()
    extras: Mapping[str, str] = Field(default_factory=dict)

    def hash(self) -> str:
        import hashlib
        import json

        # Create a hash of the environment specification for caching purposes
        env_dict = {
            "name": self.name,
            "python": self.python,
            "requirements": self.requirements,
            "channels": self.channels,
            "extras": self.extras,
        }
        env_json = json.dumps(env_dict, sort_keys=True)
        return hashlib.sha256(env_json.encode()).hexdigest()

    def name_with_hash(self) -> str:
        return f"{self.name}-{self.hash()[:8]}"


class EnvironmentHandle(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    provider: str
    path: Path


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
