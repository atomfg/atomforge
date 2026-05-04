from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from atomforge_core.resources.resource_models import (
    ExecutionResources,
    ResolvedResources,
)


def _normalized_payload(payload: Any) -> Any:
    if isinstance(payload, BaseModel):
        return _normalized_payload(payload.model_dump(mode="python"))
    if isinstance(payload, dict):
        return {
            str(key): _normalized_payload(value)
            for key, value in sorted(payload.items(), key=lambda item: str(item[0]))
        }
    if isinstance(payload, (set, frozenset)):
        values = [_normalized_payload(value) for value in payload]
        return sorted(
            values,
            key=lambda value: json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
            ),
        )
    if isinstance(payload, (list, tuple)):
        return [_normalized_payload(value) for value in payload]
    if isinstance(payload, Enum):
        return payload.value
    if isinstance(payload, (date, datetime)):
        return payload.isoformat()
    if isinstance(payload, Path):
        return str(payload)
    return payload


def payload_hash(payload: BaseModel | dict[str, Any]) -> str:
    serialized = json.dumps(
        _normalized_payload(payload),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode()).hexdigest()


class TaskProvenance(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: str
    payload_hash: str


class ModelProvenance(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: str
    payload_hash: str
    distributions: tuple[str, ...] = Field(default_factory=tuple)
    versions: dict[str, str] = Field(default_factory=dict)


class EnvironmentProvenance(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: str
    key: str
    spec_hash: str
    python: str | None = None
    requirements: tuple[str, ...] = Field(default_factory=tuple)
    provider_requirements: tuple[str, ...] = Field(default_factory=tuple)
    pyproject_hash: str | None = None
    lockfile_hash: str | None = None


class ResourceProvenance(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    requested: ExecutionResources
    resolved: ResolvedResources | None = None


class ExecutionProvenance(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    backend: str
    started_at: datetime
    ended_at: datetime
    wall_time_s: float


class Provenance(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    task: TaskProvenance
    model: ModelProvenance | None = None
    environment: EnvironmentProvenance
    resources: ResourceProvenance
    execution: ExecutionProvenance


class PartialProvenance(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    task: TaskProvenance
    model: ModelProvenance | None = None
    resources: ResourceProvenance
    execution: ExecutionProvenance
    environment_provider: str | None = None
    environment_key: str | None = None
    environment_spec_hash: str | None = None


class ExecutionErrorRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    error_type: str
    message: str
    worker_traceback: str | None = None


class ExecutionRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    status: Literal["success", "error", "incompatibility"]
    phase: Literal[
        "input_validation",
        "environment_preparation",
        "model_preparation",
        "task_execution",
        "result_validation",
    ]
    result: BaseModel | None = None
    provenance: Provenance | None = None
    partial_provenance: PartialProvenance | None = None
    error: ExecutionErrorRecord | None = None

    @field_validator("result")
    @classmethod
    def _validate_result(cls, value: BaseModel | None) -> BaseModel | None:
        if value is None:
            return value

        from atomforge_core.task.result import TaskResult

        if not isinstance(value, TaskResult):
            raise TypeError("ExecutionRecord.result must be a TaskResult")
        return value

    @model_validator(mode="after")
    def _validate_record_shape(self) -> "ExecutionRecord":
        if self.status == "success":
            if self.result is None:
                raise ValueError("Successful ExecutionRecord requires result")
            if self.provenance is None:
                raise ValueError("Successful ExecutionRecord requires provenance")
            if self.error is not None:
                raise ValueError("Successful ExecutionRecord must not include error")
        else:
            if self.error is None:
                raise ValueError("Unsuccessful ExecutionRecord requires error")
            if self.result is not None:
                raise ValueError("Unsuccessful ExecutionRecord must not include result")
            if self.provenance is None and self.partial_provenance is None:
                raise ValueError(
                    "Unsuccessful ExecutionRecord requires provenance or partial_provenance"
                )
        return self
