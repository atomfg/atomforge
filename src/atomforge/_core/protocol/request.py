from typing import Literal
from pydantic import BaseModel, ConfigDict

from typing import Any, Annotated
from pydantic import Field, TypeAdapter
from atomforge._core.resources.resource_models import ExecutionResources


class ShutdownRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    operation: Literal["shutdown"] = "shutdown"
    request_id: str


class InitModelRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    operation: Literal["init_model"] = "init_model"
    request_id: str
    model_kind: str
    model_payload: dict[str, Any]
    exec_resources: ExecutionResources


class TaskRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    operation: Literal["task"] = "task"
    request_id: str
    model_session_id: str
    task_kind: str
    task_payload: dict[str, Any]


RequestMessage = Annotated[
    TaskRequest | ShutdownRequest | InitModelRequest, Field(discriminator="operation")
]

_REQUEST_ADAPTER = TypeAdapter(RequestMessage)
