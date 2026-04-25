from pydantic import BaseModel, ConfigDict
from typing import Any, Annotated, Literal
from pydantic import Field, TypeAdapter

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


class ErrorResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    operation: Literal["error"] = "error"
    request_id: str
    error: str
    message: str | None = None
    traceback: str | None = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    operation: Literal["task"] = "task"
    request_id: str
    task_kind: str
    result_payload: dict[str, Any]


ResponseMessage = Annotated[
    TaskResponse | ShutdownResponse | ErrorResponse | InitModelResponse,
    Field(discriminator="operation"),
]

_RESPONSE_ADAPTER = TypeAdapter(ResponseMessage)
