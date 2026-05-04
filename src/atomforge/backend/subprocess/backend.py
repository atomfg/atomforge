from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from atomforge.backend.subprocess._environment import (
    get_environment_session as _get_environment_session,
    retrieve_environment_session as _retrieve_environment_session,
    setup_environment as _setup_environment,
)
from atomforge.backend.subprocess._execution import (
    ExecutionAttempt,
    end_timing,
    error_from_exception,
    error_from_worker,
)
from atomforge.backend.subprocess._model_session import (
    cache_prepared_model_session as _cache_prepared_model_session,
    prepare_init_model_request as _prepare_init_model_request,
)
from atomforge.backend.subprocess._transport import (
    send_request_and_get_response as _send_request_and_get_response,
    send_shutdown_request as _send_shutdown_request,
)
from atomforge.env.uv import UVEnvironmentProvider
from atomforge.settings.settings import AtomforgeSettings
from atomforge_core.env.env import EnvironmentSpec
from atomforge_core.model.spec import ModelSpec
from atomforge_core.protocol.request import (
    ShutdownRequest,
    TaskRequest,
)
from atomforge_core.protocol.session import model_session_key
from atomforge_core.provenance import ExecutionErrorRecord, ExecutionRecord
from atomforge_core.resources.resource_models import ExecutionResources
from atomforge_core.task.execution_policy import ExecutionPolicy
from atomforge_core.task.result import TaskResult
from atomforge_core.task.spec import TaskSpec
from atomforge_runtime.registry.model.model_registry import ModelRegistry
from atomforge_runtime.registry.task.task_registry import TaskRegistry
from atomforge_runtime.task.resolution import resolve_host_execution

if TYPE_CHECKING:
    from atomforge.backend.subprocess._environment import PreparedEnvironmentSession
    from atomforge.backend.subprocess._model_session import PreparedModelSession
    from atomforge.backend.subprocess._transport import EnvSubprocess


class SubprocessBackend:
    def __init__(self, settings: AtomforgeSettings | None = None) -> None:
        if settings is None:
            settings = AtomforgeSettings()
        if settings.env_provider_kind == "uv":
            self._environment_provider = UVEnvironmentProvider(
                search_path=settings.env_search_paths,
                install_path=settings.env_install_path,
            )

        self.env_subprocesses: dict[str, EnvSubprocess] = {}
        self.prepared_environments: dict[str, PreparedEnvironmentSession] = {}
        self.prepared_models: dict[tuple[str, str], PreparedModelSession] = {}

        self._task_registry = TaskRegistry.default()
        self._model_registry = ModelRegistry.default()
        self._settings = settings

    def setup_environment(
        self, model_spec: ModelSpec | None, task_env_spec: EnvironmentSpec
    ) -> EnvironmentSpec:
        return _setup_environment(
            model_spec=model_spec,
            task_env_spec=task_env_spec,
            model_registry=self._model_registry,
        )

    def get_environment_session(
        self, env_spec: EnvironmentSpec
    ) -> PreparedEnvironmentSession:
        return _get_environment_session(
            env_spec=env_spec,
            environment_provider=self._environment_provider,
            prepared_environments=self.prepared_environments,
            env_subprocesses=self.env_subprocesses,
        )

    def get_subprocess(self, env_spec: EnvironmentSpec) -> EnvSubprocess:
        return self.get_environment_session(env_spec).env_subprocess

    def prepare_model(
        self,
        model_spec: ModelSpec,
        task_spec: TaskSpec,
        exec_resources: ExecutionResources,
    ) -> None:
        env_session = _retrieve_environment_session(
            task=task_spec,
            model_spec=model_spec,
            task_registry=self._task_registry,
            model_registry=self._model_registry,
            environment_provider=self._environment_provider,
            prepared_environments=self.prepared_environments,
            env_subprocesses=self.env_subprocesses,
        )

        request = _prepare_init_model_request(
            model_spec=model_spec,
            exec_resources=exec_resources,
            env_subprocess=env_session.env_subprocess,
        )

        response = _send_request_and_get_response(
            env_session.env_subprocess,
            request,
        )

        if response.operation == "error":
            raise RuntimeError(response.error or "Worker returned an unknown error")

        _cache_prepared_model_session(
            model_spec=model_spec,
            exec_resources=exec_resources,
            env_session=env_session,
            response=response,
            prepared_models=self.prepared_models,
        )

    def execute(
        self,
        task: TaskSpec,
        model: ModelSpec | None = None,
        exec_resources: ExecutionResources | None = None,
    ) -> TaskResult:
        record = self.try_execute(task, model=model, exec_resources=exec_resources)
        if record.status == "success" and record.result is not None:
            return record.result

        message = (
            record.error.message
            if record.error is not None
            else "Execution failed without an error record"
        )
        if record.status == "incompatibility" or record.phase == "input_validation":
            raise ValueError(message)
        raise RuntimeError(message)

    def try_execute(
        self,
        task: TaskSpec,
        model: ModelSpec | None = None,
        exec_resources: ExecutionResources | None = None,
    ) -> ExecutionRecord:
        if exec_resources is None:
            exec_resources = ExecutionResources()

        started_at = datetime.now(timezone.utc)
        started_perf = time.perf_counter()
        attempt = ExecutionAttempt(
            backend=self,
            task=task,
            model=model,
            exec_resources=exec_resources,
            started_at=started_at,
            started_perf=started_perf,
        )

        if task.requires_model and model is None:
            return attempt.input_error(
                f"Task of kind {task.kind} requires a model, but none was provided"
            )
        if not task.requires_model and model is not None:
            return attempt.input_error(
                f"Task of kind {task.kind} is model-free and must not be given a model"
            )
        if (
            not task.requires_model
            and task.execution_policy is ExecutionPolicy.REQUIRE_MODEL_OVERRIDE
        ):
            return attempt.input_error(
                f"Task of kind {task.kind} is model-free and cannot require a model override"
            )

        task_registration = self._task_registry.get(task.kind)
        model_registration = (
            self._model_registry.get(model.kind) if model is not None else None
        )
        report = resolve_host_execution(task, task_registration, model_registration)
        if not report.ok:
            return attempt.partial_record(
                status="incompatibility",
                phase="input_validation",
                error=ExecutionErrorRecord(
                    error_type="Incompatibility",
                    message=report.reason or "Task is not executable",
                ),
            )

        env_spec = None
        try:
            task_env_spec = task_registration.load_environment_factory()(task)
            env_spec = self.setup_environment(model, task_env_spec)
            env_session = self.get_environment_session(env_spec)
        except Exception as exc:
            return attempt.partial_record(
                status="error",
                phase="environment_preparation",
                error=error_from_exception(exc),
                env_spec=env_spec,
            )

        prepared, model_error = self._prepare_model_session_for_attempt(
            attempt=attempt,
            env_session=env_session,
        )
        if model_error is not None:
            return model_error

        resolved_resources = None if prepared is None else prepared.resolved_resources
        request = TaskRequest(
            operation="task",
            request_id=str(env_session.env_subprocess.get_request_counter()),
            model_session_id=None if prepared is None else prepared.model_session_id,
            task_kind=task.kind,
            task_payload=task.model_dump(),
        )

        try:
            response = _send_request_and_get_response(
                env_session.env_subprocess,
                request,
            )
        except Exception as exc:
            return attempt.partial_record(
                status="error",
                phase="task_execution",
                resolved_resources=resolved_resources,
                error=error_from_exception(exc),
                env_session=env_session,
            )
        ended_at, wall_time_s = end_timing(started_perf)

        if response.operation == "error":
            return attempt.full_error_record(
                status="error",
                phase="task_execution",
                env_session=env_session,
                resolved_resources=resolved_resources,
                ended_at=ended_at,
                wall_time_s=wall_time_s,
                error=error_from_worker(response),
            )
        if response.operation == "incompatibility":
            return attempt.full_error_record(
                status="incompatibility",
                phase="task_execution",
                env_session=env_session,
                resolved_resources=resolved_resources,
                ended_at=ended_at,
                wall_time_s=wall_time_s,
                error=ExecutionErrorRecord(
                    error_type="Incompatibility",
                    message=response.reason,
                ),
            )

        try:
            registration = self._task_registry.get(response.task_kind)
            result = registration.load_result_model().model_validate(
                response.result_payload
            )
            if not isinstance(result, TaskResult):
                raise TypeError(
                    f"Result model for task {response.task_kind} did not return TaskResult"
                )
        except Exception as exc:
            return attempt.full_error_record(
                status="error",
                phase="result_validation",
                env_session=env_session,
                resolved_resources=resolved_resources,
                ended_at=ended_at,
                wall_time_s=wall_time_s,
                error=error_from_exception(exc),
            )

        return attempt.success_record(
            result=result,
            env_session=env_session,
            resolved_resources=resolved_resources,
            ended_at=ended_at,
            wall_time_s=wall_time_s,
        )

    def _prepare_model_session_for_attempt(
        self,
        *,
        attempt: ExecutionAttempt,
        env_session: PreparedEnvironmentSession,
    ) -> tuple[PreparedModelSession | None, ExecutionRecord | None]:
        if attempt.model is None:
            return None, None

        model_cache_key = model_session_key(attempt.model, attempt.exec_resources)
        cache_key = (model_cache_key, env_session.env_key)
        prepared = self.prepared_models.get(cache_key)
        if (
            prepared is not None
            and prepared.process_uuid == env_session.env_subprocess.process_uuid
        ):
            return prepared, None

        self.prepared_models.pop(cache_key, None)
        try:
            init_request = _prepare_init_model_request(
                model_spec=attempt.model,
                exec_resources=attempt.exec_resources,
                env_subprocess=env_session.env_subprocess,
            )
            init_response = _send_request_and_get_response(
                env_session.env_subprocess,
                init_request,
            )
        except Exception as exc:
            return None, attempt.partial_record(
                status="error",
                phase="model_preparation",
                error=error_from_exception(exc),
                env_session=env_session,
            )

        error_record = self._model_preparation_error_record(
            attempt=attempt,
            env_session=env_session,
            init_response=init_response,
        )
        if error_record is not None:
            return None, error_record

        _cache_prepared_model_session(
            model_spec=attempt.model,
            exec_resources=attempt.exec_resources,
            env_session=env_session,
            response=init_response,
            prepared_models=self.prepared_models,
        )
        return self.prepared_models[cache_key], None

    def _model_preparation_error_record(
        self,
        *,
        attempt: ExecutionAttempt,
        env_session: PreparedEnvironmentSession,
        init_response,
    ) -> ExecutionRecord | None:
        if init_response.operation == "init_model":
            return None
        if init_response.operation == "error":
            error = error_from_worker(init_response)
        else:
            error = ExecutionErrorRecord(
                error_type="UnexpectedResponse",
                message=f"Expected init_model response, got {init_response.operation}",
            )
        return attempt.partial_record(
            status="error",
            phase="model_preparation",
            error=error,
            env_session=env_session,
        )

    def send_shutdown(self, env_key: str) -> None:
        env_subprocess = self.env_subprocesses.get(env_key, None)

        if env_subprocess is None:
            print(f"No subprocess found for environment {env_key}, skipping shutdown.")
            return

        request = ShutdownRequest(
            operation="shutdown",
            request_id=str(env_subprocess.get_request_counter()),
        )
        response = _send_shutdown_request(env_subprocess, request)
        if response is not None:
            if response.operation == "error":
                print(f"Worker error during shutdown: {response.error}", flush=True)
            elif response.operation == "shutdown":
                pass
            else:
                print(f"Unexpected response during shutdown: {response}", flush=True)
        else:
            print(
                f"No response received during shutdown of worker {env_key}",
                flush=True,
            )

        env_subprocess._process.wait()
        del self.env_subprocesses[env_key]
        self.prepared_environments.pop(env_key, None)

        to_delete = []
        for (model_cache_key, cache_env_key), session in self.prepared_models.items():
            if session.process_uuid == env_subprocess.process_uuid:
                to_delete.append((model_cache_key, cache_env_key))
        for key in to_delete:
            del self.prepared_models[key]

    def shutdown(self) -> None:
        for env_key in list(self.env_subprocesses.keys()):
            self.send_shutdown(env_key)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()
