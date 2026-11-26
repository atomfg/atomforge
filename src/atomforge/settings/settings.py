import os
import types
from typing import Any, Literal, Union, get_args, get_origin
from pathlib import Path
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)
from os import pathsep

_IGNORE_ENVIRONMENT = "ignore_environment"


def _accepts_none(annotation: Any) -> bool:
    return get_origin(annotation) in (Union, types.UnionType) and type(
        None
    ) in get_args(annotation)


class AtomforgeSettings(BaseModel):
    """Settings of the host side.

    A field not given as an argument is read from the environment variable
    its metadata names (``env_var``), and otherwise takes its default. For an
    optional timeout, the value ``none`` (any case) means no timeout.
    """

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
        default=1800.0,
        gt=0,
        description="Seconds to wait for a worker to initialize a model (includes checkpoint downloads). Defaults to 30 minutes. None waits indefinitely. On timeout the worker is killed.",
        json_schema_extra={"env_var": "ATOMFORGE_WORKER_INIT_TIMEOUT_S"},
    )
    worker_task_timeout_s: float | None = Field(
        default=3600.0,
        gt=0,
        description="Default seconds to wait for a worker to finish one task. Defaults to 1 hour. None waits indefinitely. Can be overridden per call. On timeout the worker is killed.",
        json_schema_extra={"env_var": "ATOMFORGE_WORKER_TASK_TIMEOUT_S"},
    )
    worker_shutdown_timeout_s: float = Field(
        default=10.0,
        gt=0,
        description="Seconds to wait for a worker to exit after a shutdown request before killing it.",
        json_schema_extra={"env_var": "ATOMFORGE_WORKER_SHUTDOWN_TIMEOUT_S"},
    )

    @classmethod
    def environment_variables(cls) -> dict[str, str]:
        """Field name -> the environment variable it is read from."""
        return {
            name: field.json_schema_extra["env_var"]
            for name, field in cls.model_fields.items()
            if isinstance(field.json_schema_extra, dict)
            and "env_var" in field.json_schema_extra
        }

    @model_validator(mode="before")
    @classmethod
    def _read_environment(cls, data: Any, info: ValidationInfo) -> Any:
        if info.context and info.context.get(_IGNORE_ENVIRONMENT):
            return data
        if not isinstance(data, dict):
            return data
        data = dict(data)
        for name, variable in cls.environment_variables().items():
            if name in data or variable not in os.environ:
                continue
            raw = os.environ[variable]
            value: Any = raw
            if raw.strip().lower() == "none" and _accepts_none(
                cls.model_fields[name].annotation
            ):
                value = None
            try:
                cls.model_validate({name: value}, context={_IGNORE_ENVIRONMENT: True})
            except ValidationError as error:
                reason = error.errors()[0]["msg"]
                raise ValueError(
                    f"environment variable {variable}={raw!r} is not a valid "
                    f"{name}: {reason}"
                ) from None
            data[name] = value
        return data

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
