from __future__ import annotations

import contextlib
import sys
import os
import traceback
from typing import Any, TextIO

from pydantic import ValidationError

from atomforge.backend.base.resources import (
    discover_system_resources,
    resolve_resources,
    SystemResources,
)
from atomforge.backend.base.session import model_session_key
from atomforge.model.core.executor import ModelExecutor
from atomforge.model.core.spec import ModelSpec
from atomforge.registry.model.registry import ModelRegistry

from atomforge.registry.task.registry import TaskRegistry
from atomforge.task.core.resources import ResolvedResources

from atomforge.backend.subprocess.core import (
    read_request,
    write_response,
)
from atomforge.backend.subprocess.request import (
    ShutdownRequest,
    TaskRequest,
    InitModelRequest,
)
from atomforge.backend.subprocess.response import (
    InitModelResponse,
    TaskResponse,
    ShutdownResponse,
    ErrorResponse,
)


class SubprocessWorker:
    def __init__(
        self,
        stdin: TextIO,
        stdout: TextIO,
        stderr: TextIO,
        name: str,
        task_registry: TaskRegistry,
        model_registry: ModelRegistry,
        system_resources: SystemResources,
    ) -> None:
        self._stdin = stdin
        self._stdout = stdout
        self._stderr = stderr
        self._name = name
        self._task_registry = task_registry
        self._model_registry = model_registry
        self._system_resources = system_resources

        self._model_sessions: dict[str, ModelExecutor] = {}
        self._dev_null = open(os.devnull, "w")

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
            case "init_model":
                return self._init_model_case(request)
            case "task":
                return self._task_execution_case(request)
            case _:
                return ErrorResponse(
                    request_id=request.request_id,
                    error=f"unknown operation: {request.operation}",
                ), False

    def _init_model_case(self, request: InitModelRequest) -> tuple[TaskResponse, bool]:
        try:
            model_executor, resolved_resources = self._create_model_executor(request)
        except Exception as exc:
            traceback.print_exc(file=self._stderr)
            return self._failed_execution_case(request.request_id, exc)

        model_session_id = self._get_model_session_id(request)
        self._model_sessions[model_session_id] = model_executor

        return InitModelResponse(
            request_id=request.request_id,
            model_session_id=model_session_id,
            resolved_resources=resolved_resources,
        ), False

    def _get_model_spec(self, request: InitModelRequest) -> ModelSpec:
        model_registration = self._model_registry.get(request.model_kind)
        model_spec = model_registration.model_spec.model_validate(request.model_payload)
        return model_spec

    def _get_model_session_id(self, request: InitModelRequest) -> str:
        model_spec = self._get_model_spec(request)
        model_session_id = model_session_key(model_spec, request.exec_resources)
        return model_session_id

    def _get_model_executor(self, model_session_id: str) -> ModelExecutor:
        model_executor = self._model_sessions.get(model_session_id)
        if model_executor is None:
            raise ValueError(f"unknown model session id: {model_session_id}")
        return model_executor

    def _create_model_executor(
        self, request: InitModelRequest
    ) -> tuple[ModelExecutor, ResolvedResources]:
        # Get the ExecResources from the request
        with contextlib.redirect_stdout(self._dev_null) as _:
            with contextlib.redirect_stderr(self._dev_null) as _:
                model_registration = self._model_registry.get(request.model_kind)
                model_spec = model_registration.model_spec.model_validate(
                    request.model_payload
                )

                if model_registration.probe is not None:
                    probe_result = model_registration.probe(model_spec)
                else:
                    probe_result = None

                resource_capabilities = model_registration.resource_capabilities
                resolved_resources = resolve_resources(
                    exec_resources=request.exec_resources,
                    system_resources=self._system_resources,
                    resource_caps=resource_capabilities,
                    probe_result=probe_result,
                )

                model_executor = model_registration.executor_class(
                    model_spec, resolved_resources
                )

        return model_executor, resolved_resources

    def _execute_task(self, request: TaskRequest) -> Any:
        # Validate the model and task payloads and construct the executors
        task_registration = self._task_registry.get(request.task_kind)
        task_spec = task_registration.spec_model.model_validate(request.task_payload)
        task_executor = task_registration.executor_class()

        # Get the model executor for the task
        model_executor = self._get_model_executor(request.model_session_id)

        # Context manager that ensures nothing is written to stdout during model execution
        with contextlib.redirect_stdout(self._dev_null) as _:
            with contextlib.redirect_stderr(self._dev_null) as _:
                task_result = task_executor.execute(task_spec, model_executor)

        return TaskResponse(
            request_id=request.request_id,
            task_kind=request.task_kind,
            result_payload=task_result.model_dump(),
        )

    def _log(self, message: str) -> None:
        print(f"worker[{self._name}]: {message}", file=self._stderr, flush=True)


def main(name: str) -> int: # pragma: no cover
    task_registry = TaskRegistry.default()
    model_registry = ModelRegistry.default()
    system_resources = discover_system_resources()

    worker = SubprocessWorker(
        stdin=sys.stdin,
        stdout=sys.stdout,
        stderr=sys.stderr,
        name=name,
        task_registry=task_registry,
        model_registry=model_registry,
        system_resources=system_resources,
    )
    return worker.run()


if __name__ == "__main__": # pragma: no cover
    import sys 
    name = sys.argv[1]
    raise SystemExit(main(name))
