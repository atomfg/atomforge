from pydantic import BaseModel, ConfigDict
from typing import Any, Annotated, Literal
from pydantic import Field, TypeAdapter

from atomforge_core.protocol.diagnostics import WorkerDiagnostics
from atomforge_core.resources.resource_models import ResolvedResources


class ShutdownResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    operation: Literal["shutdown"] = "shutdown"
    request_id: str
    message: str | None = None


class InitModelResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    operation: Literal["init_model"] = "init_model"
    request_id: str
    model_session_id: str
    resolved_resources: ResolvedResources
    diagnostics: WorkerDiagnostics | None = None


class ErrorResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    operation: Literal["error"] = "error"
    request_id: str
    error: str
    message: str | None = None
    traceback: str | None = None
    diagnostics: WorkerDiagnostics | None = None


class IncompatibilityResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    operation: Literal["incompatibility"] = "incompatibility"
    request_id: str
    task_kind: str
    reason: str
    route_kind: str | None = None
    diagnostics: WorkerDiagnostics | None = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    operation: Literal["task"] = "task"
    request_id: str
    task_kind: str
    result_payload: dict[str, Any]
    diagnostics: WorkerDiagnostics | None = None


ResponseMessage = Annotated[
    TaskResponse
    | ShutdownResponse
    | ErrorResponse
    | InitModelResponse
    | IncompatibilityResponse,
    Field(discriminator="operation"),
]

_RESPONSE_ADAPTER = TypeAdapter(ResponseMessage)
