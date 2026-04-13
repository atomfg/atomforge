from typing import Literal
from pydantic import BaseModel, ConfigDict

from typing import TextIO, Any

class ComputeRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    operation: Literal['task', 'shutdown']
    request_id: str
    model_name: str
    task_kind: str
    task_payload: dict[str, Any]

class ComputeResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    request_id: str
    ok: bool
    task_kind: str | None = None
    result_payload: dict[str, Any] | None = None
    error: str | None = None
    message: str | None = None

def _write_message(stream: TextIO, message: BaseModel) -> None:
    stream.write(message.model_dump_json())
    stream.write("\n")
    stream.flush()


def write_request(stream: TextIO, request: ComputeRequest) -> None:
    _write_message(stream, request)


def write_response(stream: TextIO, response: ComputeResponse) -> None:
    _write_message(stream, response)


def read_request(stream: TextIO) -> ComputeRequest | None:
    line = stream.readline()
    if line == "":
        return None

    return ComputeRequest.model_validate_json(line)


def read_response(stream: TextIO) -> ComputeResponse | None:
    line = stream.readline()
    if line == "":
        return None

    return ComputeResponse.model_validate_json(line)