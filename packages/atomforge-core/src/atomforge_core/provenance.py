from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

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
