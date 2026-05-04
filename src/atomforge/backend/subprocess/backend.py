import subprocess
import time
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from atomforge_core.protocol.session import model_session_key
from atomforge_core.env.env import EnvironmentSpec
from atomforge.env.uv import UVEnvironmentProvider
from atomforge_core.model.spec import ModelSpec
from atomforge_runtime.registry.model.model_registry import ModelRegistry
from atomforge_runtime.registry.task.task_registry import TaskRegistry
from atomforge.settings.settings import AtomforgeSettings
from atomforge_core.resources.resource_models import ExecutionResources, ResolvedResources
from atomforge_core.provenance import (
    ExecutionProvenance,
    ModelProvenance,
    Provenance,
    ResourceProvenance,
    TaskProvenance,
    payload_hash,
)
from atomforge_core.task.execution_policy import ExecutionPolicy
from atomforge_core.task.result import TaskResult
from atomforge_core.task.spec import TaskSpec

from atomforge_core.protocol.core import read_response, write_request
from atomforge_core.protocol.request import TaskRequest, ShutdownRequest, RequestMessage, InitModelRequest
from atomforge_core.protocol.response import ResponseMessage
from atomforge_runtime.task.resolution import resolve_host_execution

from dataclasses import dataclass
from uuid import uuid4


@dataclass
class PreparedModelSession:
    model_spec: ModelSpec
    model_session_id: str
    execution_resources: ExecutionResources
    resolved_resources: ResolvedResources
    process_uuid: str


@dataclass
class PreparedEnvironmentSession:
    env_spec: EnvironmentSpec
    env_key: str
    env_subprocess: "EnvSubprocess"
    environment_provenance: object


class EnvSubprocess:
    def __init__(self, executeable: Path, name: str) -> None:
        self.process_uuid = str(uuid4())
        self._request_counter = 0
        self._process = subprocess.Popen(
            [executeable.as_posix(), "-m", "atomforge_runtime.backend.subprocess.worker", name],
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
        if model_spec is None:
            return task_env_spec

        model_env_spec = self._model_registry.get(model_spec.kind).load_environment_factory()(
            model_spec
        )
        return model_env_spec + task_env_spec

    def get_environment_session(
        self, env_spec: EnvironmentSpec
    ) -> PreparedEnvironmentSession:
        env_key = self._environment_provider.environment_key(env_spec)

        prepared = self.prepared_environments.get(env_key)
        if prepared is not None:
            return prepared

        handle = self._environment_provider.ensure_environment(env_spec)
        info = self._environment_provider.inspect_environment(handle)
        env_subprocess = EnvSubprocess(info.python_executable, name=env_key)
        environment_provenance = self._environment_provider.build_provenance(
            env_spec,
            handle,
        )
        prepared = PreparedEnvironmentSession(
            env_spec=env_spec,
            env_key=env_key,
            env_subprocess=env_subprocess,
            environment_provenance=environment_provenance,
        )
        self.prepared_environments[env_key] = prepared
        self.env_subprocesses[env_key] = env_subprocess
        return prepared

    def get_subprocess(self, env_spec: EnvironmentSpec) -> EnvSubprocess:
        return self.get_environment_session(env_spec).env_subprocess

    def _ensure_matching_response(
        self, request: RequestMessage, response: ResponseMessage
    ) -> None:
        if response.request_id != request.request_id:
            raise RuntimeError(
                f"Response id mismatch: expected {request.request_id}, got {response.request_id}"
            )

    def _send_request_and_get_response(
        self, env_subprocess: EnvSubprocess, request: RequestMessage
    ) -> ResponseMessage:
        write_request(env_subprocess._stdin, request)
        response = read_response(env_subprocess._stdout)
        self._ensure_matching_response(request, response)
        return response

    def _validate_task_executability(
        self, model_spec: ModelSpec | None, task_spec: TaskSpec
    ) -> None:
        task_registration = self._task_registry.get(task_spec.kind)
        model_registration = (
            self._model_registry.get(model_spec.kind) if model_spec is not None else None
        )
        report = resolve_host_execution(
            task_spec,
            task_registration,
            model_registration,
        )
        if not report.ok:
            raise ValueError(report.reason or "Task is not executable")

    def _distribution_versions(self, distributions: list[str]) -> dict[str, str]:
        versions = {}
        for distribution in distributions:
            try:
                versions[distribution] = version(distribution)
            except PackageNotFoundError:
                continue
        return versions

    def _build_provenance(
        self,
        *,
        task: TaskSpec,
        model: ModelSpec | None,
        environment_provenance,
        exec_resources: ExecutionResources,
        resolved_resources: ResolvedResources | None,
        started_at: datetime,
        ended_at: datetime,
        wall_time_s: float,
    ) -> Provenance:
        model_provenance = None
        if model is not None:
            model_registration = self._model_registry.get(model.kind)
            distributions = tuple(model_registration.source)
            model_provenance = ModelProvenance(
                kind=model.kind,
                payload_hash=payload_hash(model),
                distributions=distributions,
                versions=self._distribution_versions(list(distributions)),
            )

        return Provenance(
            task=TaskProvenance(
                kind=task.kind,
                payload_hash=payload_hash(task),
            ),
            model=model_provenance,
            environment=environment_provenance,
            resources=ResourceProvenance(
                requested=exec_resources,
                resolved=resolved_resources,
            ),
            execution=ExecutionProvenance(
                backend="subprocess",
                started_at=started_at,
                ended_at=ended_at,
                wall_time_s=wall_time_s,
            ),
        )

    def _attach_provenance(
        self, result: TaskResult, provenance: Provenance
    ) -> TaskResult:
        if isinstance(result, TaskResult):
            return result.model_copy(update={"provenance": provenance})
        setattr(result, "provenance", provenance)
        return result

    def _retrieve_environment_session(
        self,
        task: TaskSpec,
        model_spec: ModelSpec | None,
    ) -> PreparedEnvironmentSession:
        task_registration = self._task_registry.get(task.kind)
        task_env_spec = task_registration.load_environment_factory()(task)
        env_spec = self.setup_environment(model_spec, task_env_spec)
        return self.get_environment_session(env_spec)

    def _retrieve_prepared_model_session(
        self,
        model_spec: ModelSpec,
        task: TaskSpec,
        exec_resources: ExecutionResources,
        env_session: PreparedEnvironmentSession,
    ) -> PreparedModelSession:
        # Check if we have already prepared this model with the same execution resources
        # in this subprocess, if not prepare it by sending an init_model_request.
        model_cache_key = model_session_key(model_spec, exec_resources)
        env_cache_key = env_session.env_key
        prepared = self.prepared_models.get((model_cache_key, env_cache_key))

        if (
            prepared is None
            or prepared.process_uuid != env_session.env_subprocess.process_uuid
        ):
            self.prepared_models.pop((model_cache_key, env_cache_key), None)
            self.prepare_model(model_spec, task, exec_resources)
            prepared = self.prepared_models[(model_cache_key, env_cache_key)]
        return prepared

    def _prepare_init_model_request(
        self,
        model_spec: ModelSpec,
        exec_resources: ExecutionResources,
        env_subprocess: EnvSubprocess,
    ) -> InitModelRequest:
        return InitModelRequest(
            request_id=str(env_subprocess.get_request_counter()),
            model_kind=model_spec.kind,
            model_payload=model_spec.model_dump(),
            exec_resources=exec_resources,
        )

    def prepare_model(
        self,
        model_spec: ModelSpec,
        task_spec: TaskSpec,
        exec_resources: ExecutionResources,
    ) -> None:

        # Get the environment and subprocess for this model and task
        env_session = self._retrieve_environment_session(task_spec, model_spec)

        request = self._prepare_init_model_request(
            model_spec, exec_resources, env_session.env_subprocess
        )

        response = self._send_request_and_get_response(
            env_session.env_subprocess,
            request,
        )

        if response.operation == "error":
            raise RuntimeError(response.error or "Worker returned an unknown error")

        model_session_id = response.model_session_id
        model_cache_key = model_session_key(model_spec, exec_resources)

        self.prepared_models[(model_cache_key, env_session.env_key)] = (
            PreparedModelSession(
                model_spec=model_spec,
                model_session_id=model_session_id,
                execution_resources=exec_resources,
                resolved_resources=response.resolved_resources,
                process_uuid=env_session.env_subprocess.process_uuid,
            )
        )

    def execute(
        self,
        task: TaskSpec,
        model: ModelSpec | None = None,
        exec_resources: ExecutionResources | None = None,
    ) -> TaskResult:

        if exec_resources is None:
            exec_resources = ExecutionResources()

        if task.requires_model and model is None:
            raise ValueError(
                f"Task of kind {task.kind} requires a model, but none was provided"
            )
        if not task.requires_model and model is not None:
            raise ValueError(
                f"Task of kind {task.kind} is model-free and must not be given a model"
            )
        if (
            not task.requires_model
            and task.execution_policy is ExecutionPolicy.REQUIRE_MODEL_OVERRIDE
        ):
            raise ValueError(
                f"Task of kind {task.kind} is model-free and cannot require a model override"
            )

        # Check that the model can support the task before starting the subprocess
        self._validate_task_executability(model, task)

        # Setup / Retrieve the environment and subprocess for this task
        env_session = self._retrieve_environment_session(task, model)

        # Check if we have already prepared this model with the same execution resources
        # in this subprocess, if not prepare it by sending an init_model_request.
        prepared = None
        if model is not None:
            prepared = self._retrieve_prepared_model_session(
                model, task, exec_resources, env_session
            )

        # Convert to a TaskRequest
        request = TaskRequest(
            operation="task",
            request_id=str(env_session.env_subprocess.get_request_counter()),
            model_session_id=None if prepared is None else prepared.model_session_id,
            task_kind=task.kind,
            task_payload=task.model_dump(),
        )

        # Send the request to the subprocess
        started_at = datetime.now(timezone.utc)
        started_perf = time.perf_counter()
        response = self._send_request_and_get_response(
            env_session.env_subprocess,
            request,
        )
        ended_at = datetime.now(timezone.utc)
        wall_time_s = time.perf_counter() - started_perf

        if response.operation == "error":
            raise RuntimeError(response.error or "Worker returned an unknown error")
        if response.operation == "incompatibility":
            raise ValueError(response.reason)

        # Convert to a TaskResult of the appropriate type based on the task kind
        registration = self._task_registry.get(response.task_kind)
        result = registration.load_result_model().model_validate(response.result_payload)

        if not isinstance(result, TaskResult):
            return result

        provenance = self._build_provenance(
            task=task,
            model=model,
            environment_provenance=env_session.environment_provenance,
            exec_resources=exec_resources,
            resolved_resources=None if prepared is None else prepared.resolved_resources,
            started_at=started_at,
            ended_at=ended_at,
            wall_time_s=wall_time_s,
        )

        return self._attach_provenance(result, provenance)

    def send_shutdown(self, env_key: str) -> None:
        env_subprocess = self.env_subprocesses.get(env_key, None)

        if env_subprocess is not None:
            request = ShutdownRequest(
                operation="shutdown",
                request_id=str(env_subprocess.get_request_counter()),
            )
            write_request(env_subprocess._stdin, request)
            response = read_response(env_subprocess._stdout)
            if response is not None:
                self._ensure_matching_response(request, response)
                if response.operation == "error":
                    print(f"Worker error during shutdown: {response.error}", flush=True)
                elif response.operation == "shutdown":
                    pass
                else:
                    print(
                        f"Unexpected response during shutdown: {response}", flush=True
                    )
            else:
                print(
                    f"No response received during shutdown of worker {env_key}",
                    flush=True,
                )
            env_subprocess._process.wait()
            del self.env_subprocesses[env_key]
            self.prepared_environments.pop(env_key, None)

            # Delete any prepared model sessions associated with this subprocess
            to_delete = []
            for (
                model_cache_key,
                cache_env_key,
            ), session in self.prepared_models.items():
                if session.process_uuid == env_subprocess.process_uuid:
                    to_delete.append((model_cache_key, cache_env_key))
            for key in to_delete:
                del self.prepared_models[key]
        else:
            print(f"No subprocess found for environment {env_key}, skipping shutdown.")

    def shutdown(self) -> None:
        for env_key in list(self.env_subprocesses.keys()):
            self.send_shutdown(env_key)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()
