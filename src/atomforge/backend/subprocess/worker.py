from __future__ import annotations

import sys
from typing import Any, TextIO

from pydantic import ValidationError

from .core import (
    ComputeResponse,
    ComputeRequest,
    read_request,
    write_response,
)


class SubprocessWorker:
    def __init__(self, stdin: TextIO, stdout: TextIO, stderr: TextIO) -> None:
        self._stdin = stdin
        self._stdout = stdout
        self._stderr = stderr

    def run(self) -> int:
        self._log("started")

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

    def _handle_request(self, request) -> tuple[ComputeResponse, bool]:
        if request.operation == "shutdown":
            return (
                ComputeResponse(
                    request_id=request.request_id,
                    ok=True,
                    message="worker shutting down",
                ),
                True,
            )

        try:
            result = self._execute_task(request)
        except Exception as exc:
            return (
                ComputeResponse(
                    request_id=request.request_id,
                    ok=False,
                    error=f"{type(exc).__name__}: {exc}",
                ),
                False,
            )

        return (
            ComputeResponse(request_id=request.request_id, ok=True, result=result),
            False,
        )

    def _execute_task(self, request: ComputeRequest) -> Any:        
        from atomforge.model import models

        model = models[request.model_name]()
        structure = request.structure.to_structure()
        properties = request.properties
        self._log(f"computing {request.model_name} for structure with {len(structure)} atoms and properties {properties}")
        result = model.compute(structure, properties)
        return result.energy

    def _log(self, message: str) -> None:
        print(f"worker[pydantic]: {message}", file=self._stderr, flush=True)


def main() -> int:
    worker = SubprocessWorker(stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)
    return worker.run()


if __name__ == "__main__":
    raise SystemExit(main())
