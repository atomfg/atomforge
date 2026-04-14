from pydantic import BaseModel
from typing import TextIO

from .request import RequestMessage, _REQUEST_ADAPTER
from .response import ResponseMessage, _RESPONSE_ADAPTER


def _write_message(stream: TextIO, message: BaseModel) -> None:
    stream.write(message.model_dump_json())
    stream.write("\n")
    stream.flush()


def write_request(stream: TextIO, request: RequestMessage) -> None:
    _write_message(stream, request)


def write_response(stream: TextIO, response: ResponseMessage) -> None:
    _write_message(stream, response)


def read_request(stream: TextIO) -> RequestMessage | None:
    line = stream.readline()
    if line == "":
        return None

    return _REQUEST_ADAPTER.validate_json(line)


def read_response(stream: TextIO) -> ResponseMessage | None:
    line = stream.readline()
    if line == "":
        return None

    return _RESPONSE_ADAPTER.validate_json(line)
