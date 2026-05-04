import subprocess
from pathlib import Path
from uuid import uuid4

from atomforge_core.protocol.core import read_response, write_request
from atomforge_core.protocol.request import RequestMessage, ShutdownRequest
from atomforge_core.protocol.response import ResponseMessage


class EnvSubprocess:
    def __init__(self, executeable: Path, name: str) -> None:
        self.process_uuid = str(uuid4())
        self._request_counter = 0
        self._process = subprocess.Popen(
            [
                executeable.as_posix(),
                "-m",
                "atomforge_runtime.backend.subprocess.worker",
                name,
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=None,
            text=True,
        )

        if (
            self._process.stdin is None or self._process.stdout is None
        ):  # pragma: no cover
            raise RuntimeError("Failed to open worker pipes")

        self._stdin = self._process.stdin
        self._stdout = self._process.stdout

    def get_request_counter(self) -> int:
        self._request_counter += 1
        return self._request_counter


def ensure_matching_response(
    request: RequestMessage, response: ResponseMessage
) -> None:
    if response.request_id != request.request_id:
        raise RuntimeError(
            f"Response id mismatch: expected {request.request_id}, "
            f"got {response.request_id}"
        )


def send_request_and_get_response(
    env_subprocess: EnvSubprocess, request: RequestMessage
) -> ResponseMessage:
    write_request(env_subprocess._stdin, request)
    response = read_response(env_subprocess._stdout)
    ensure_matching_response(request, response)
    return response


def send_shutdown_request(
    env_subprocess: EnvSubprocess, request: ShutdownRequest
) -> ResponseMessage | None:
    write_request(env_subprocess._stdin, request)
    response = read_response(env_subprocess._stdout)
    if response is not None:
        ensure_matching_response(request, response)
    return response
