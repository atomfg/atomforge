from __future__ import annotations

import contextlib
import sys
import traceback
from typing import Any, TextIO

from pydantic import ValidationError

from .core import (
    ComputeRequest,
    ComputeResponse,
    read_request,
    write_response,
)

from atomforge.task.base import get_default_registry

class SubprocessWorker:
    def __init__(self, stdin: TextIO, stdout: TextIO, stderr: TextIO) -> None:
        self._stdin = stdin
        self._stdout = stdout
        self._stderr = stderr
        self._task_registry = get_default_registry()

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
                print(f"worker processed {loop_count} request(s)", file=self._stderr, flush=True)
                self._log("shutdown requested")
                return 0
            
    def _shutdown_case(self, request_id: str) -> tuple[ComputeResponse, bool]:
        return ComputeResponse(
            request_id=request_id,
            ok=True,
            message="worker shutting down",
        ), True
    
    def _failed_execution_case(self, request_id: str, exc: Exception) -> tuple[ComputeResponse, bool]:
        return ComputeResponse(
            request_id=request_id,
            ok=False,
            error=f"{type(exc).__name__}: {exc}",
        ), False

    def _handle_request(self, request) -> tuple[ComputeResponse, bool]:

        match request.operation:
            case "shutdown":
                return self._shutdown_case(request.request_id)
            case _:
                try:
                    response = self._execute_task(request)
                except Exception as exc:
                    traceback.print_exc(file=self._stderr)
                    return self._failed_execution_case(request.request_id, exc)

        return (
            response,
            False,
        )

    def _execute_task(self, request: ComputeRequest) -> Any:        
        from atomforge.model import models

        registration = self._task_registry.get(request.task_kind)
        spec = registration.spec_model.model_validate(request.task_payload)

        # Context manager that ensures nothing is written to stdout during model execution
        with contextlib.redirect_stdout(None) as _:
            with contextlib.redirect_stderr(None) as _:
                model = models[request.model_name]()
                executor = registration.executor
                task_result = executor.execute(spec, model)

        return ComputeResponse(
            request_id=request.request_id,
            ok=True,
            task_kind=request.task_kind,
            result_payload=task_result.model_dump(),
        )

    def _log(self, message: str) -> None:
        print(f"worker[pydantic]: {message}", file=self._stderr, flush=True)


def main() -> int:
    worker = SubprocessWorker(stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)
    return worker.run()


if __name__ == "__main__":
    raise SystemExit(main())
