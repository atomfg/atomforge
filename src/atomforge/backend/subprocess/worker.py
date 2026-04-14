from __future__ import annotations

import contextlib
import sys
import traceback
from typing import Any, TextIO

from pydantic import ValidationError

from .core import (
    read_request,
    write_response,
)

from .request import RequestMessage, ShutdownRequest, TaskRequest
from .response import TaskResponse, ShutdownResponse, ErrorResponse


from atomforge.task.base import get_default_task_registry
from atomforge.model import get_default_model_registry


class SubprocessWorker:
    def __init__(
        self, stdin: TextIO, stdout: TextIO, stderr: TextIO, name: str
    ) -> None:
        self._stdin = stdin
        self._stdout = stdout
        self._stderr = stderr
        self._name = name
        self._task_registry = get_default_task_registry()
        self._model_registry = get_default_model_registry()

    def run(self) -> int:
        loop_count = 0

        while True:
            loop_count += 1
            try:
                request = read_request(self._stdin)
            except ValidationError as exc:
                self._log(f"invalid request: {exc}")
                return 1

            if request is None:
                self._log("stdin closed")
                return 0

            response, should_exit = self._handle_request(request)
            write_response(self._stdout, response)

            if should_exit:
                # self._log(f"worker processed {loop_count} request(s)")
                # self._log("shutdown requested")
                return 0

    def _shutdown_case(self, request: ShutdownRequest) -> tuple[ShutdownResponse, bool]:
        return ShutdownResponse(
            request_id=request.request_id,
            message="worker shutting down",
        ), True

    def _task_execution_case(self, request: TaskRequest) -> tuple[TaskResponse, bool]:
        try:
            response = self._execute_task(request)
        except Exception as exc:
            traceback.print_exc(file=self._stderr)
            return self._failed_execution_case(request.request_id, exc)

        return response, False

    def _failed_execution_case(
        self, request_id: str, exc: Exception
    ) -> tuple[ErrorResponse, bool]:
        return ErrorResponse(
            request_id=request_id,
            error=f"{type(exc).__name__}: {exc}",
            traceback="".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__)
            ),
        ), False

    def _handle_request(self, request) -> tuple[TaskResponse, bool]:
        match request.operation:
            case "shutdown":
                return self._shutdown_case(request)
            case "task":
                return self._task_execution_case(request)
            case _:
                return ErrorResponse(
                    request_id=request.request_id,
                    error=f"unknown operation: {request.operation}",
                ), False

    def _execute_task(self, request: TaskRequest) -> Any:
        registration = self._task_registry.get(request.task_kind)
        spec = registration.spec_model.model_validate(request.task_payload)

        # Context manager that ensures nothing is written to stdout during model execution
        with contextlib.redirect_stdout(None) as _:
            with contextlib.redirect_stderr(None) as _:
                model = self._model_registry.get(request.model_kind).model_class()
                executor = registration.executor
                task_result = executor.execute(spec, model)

        return TaskResponse(
            request_id=request.request_id,
            task_kind=request.task_kind,
            result_payload=task_result.model_dump(),
        )

    def _log(self, message: str) -> None:
        print(f"worker[{self._name}]: {message}", file=self._stderr, flush=True)


def main(name: str) -> int:
    worker = SubprocessWorker(
        stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr, name=name
    )
    return worker.run()


if __name__ == "__main__":
    import sys

    name = sys.argv[1]
    raise SystemExit(main(name))
