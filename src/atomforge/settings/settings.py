from typing import Literal
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, field_validator
from os import pathsep


class AtomforgeSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    env_search_paths: tuple[Path, ...] = Field(
        default=(Path.home() / ".atomforge" / "envs",),
        description="Ordered list of directories to search for environments.",
        json_schema_extra={"env_var": "ATOMFORGE_ENV_SEARCH_PATHS"},
    )
    env_install_path: Path = Field(
        default=Path.home() / ".atomforge" / "envs",
        description="Path to install new environments.",
        json_schema_extra={"env_var": "ATOMFORGE_ENV_INSTALL_PATH"},
    )
    env_provider_kind: Literal["uv"] = Field(
        default="uv",
        description="Provider to use for managing environments.",
        json_schema_extra={"env_var": "ATOMFORGE_ENV_PROVIDER_KIND"},
    )
    worker_init_timeout_s: float | None = Field(
        default=None,
        gt=0,
        description="Seconds to wait for a worker to initialize a model (includes checkpoint downloads). None waits indefinitely. On timeout the worker is killed.",
        json_schema_extra={"env_var": "ATOMFORGE_WORKER_INIT_TIMEOUT_S"},
    )
    worker_task_timeout_s: float | None = Field(
        default=None,
        gt=0,
        description="Default seconds to wait for a worker to finish one task. None waits indefinitely. Can be overridden per call. On timeout the worker is killed.",
        json_schema_extra={"env_var": "ATOMFORGE_WORKER_TASK_TIMEOUT_S"},
    )
    worker_shutdown_timeout_s: float = Field(
        default=10.0,
        gt=0,
        description="Seconds to wait for a worker to exit after a shutdown request before killing it.",
        json_schema_extra={"env_var": "ATOMFORGE_WORKER_SHUTDOWN_TIMEOUT_S"},
    )

    @field_validator("env_search_paths", mode="before")
    def normalize_search_paths(cls, v):
        if isinstance(v, Path):
            return (v,)
        elif isinstance(v, str):
            parts = [p.strip() for p in v.split(pathsep)]
            paths = [Path(p) for p in parts if p]
            return tuple(paths)
        elif isinstance(v, (list, tuple)):
            return tuple(Path(p) for p in v)
        else:
            raise ValueError(f"Invalid path value: {v}")

    @field_validator("env_install_path", mode="before")
    def normalize_install_path(cls, v):
        if isinstance(v, str):
            return Path(v)
        elif isinstance(v, Path):
            return v
        else:
            raise ValueError(f"Invalid path value: {v}")
