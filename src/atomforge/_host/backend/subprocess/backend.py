import subprocess
from pathlib import Path

from atomforge._core.protocol.session import model_session_key
from atomforge._core.env.env import EnvironmentSpec
from atomforge._host.env.uv import UVEnvironmentProvider
from atomforge._core.model.spec import ModelSpec
from atomforge._runtime.registry.model.model_registry import ModelRegistry
from atomforge._runtime.registry.task.task_registry import TaskRegistry
from atomforge._host.settings.settings import AtomforgeSettings
from atomforge._core.resources.resource_models import ExecutionResources, ResolvedResources
from atomforge._core.task.result import TaskResult
from atomforge._core.task.spec import TaskSpec

from ...._core.protocol.core import read_response, write_request
from ...._core.protocol.request import TaskRequest, ShutdownRequest, RequestMessage, InitModelRequest
from ...._core.protocol.response import ResponseMessage

from dataclasses import dataclass
from uuid import uuid4


@dataclass
class PreparedModelSession:
    model_spec: ModelSpec
    model_session_id: str
    execution_resources: ExecutionResources
    resolved_resources: ResolvedResources
    process_uuid: str


class EnvSubprocess:
    def __init__(self, executeable: Path, name: str) -> None:
        self.process_uuid = str(uuid4())
        self._request_counter = 0
        self._process = subprocess.Popen(
            [executeable.as_posix(), "-m", "atomforge._runtime.backend.subprocess.worker", name],
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
        self.prepared_models: dict[tuple[str, str], PreparedModelSession] = {}

        self._task_registry = TaskRegistry.default()
        self._model_registry = ModelRegistry.default()
        self._settings = settings

    def setup_environment(
        self, model_spec: ModelSpec, task_env_spec: EnvironmentSpec
    ) -> EnvironmentSpec:

        # For now, we just use the default environment spec from the model,
        # but in the future we could allow tasks to specify their own environment requirements
        model_env_spec = self._model_registry.get(model_spec.kind).environment_factory(
            model_spec
        )
        # Get the subprocess for the environment
        env_spec = model_env_spec + task_env_spec

        return env_spec

    def get_subprocess(self, env_spec: EnvironmentSpec) -> EnvSubprocess:
        env_hash = env_spec.short_hash()

        if env_hash not in self.env_subprocesses:
            handle = self._environment_provider.ensure_environment(env_spec)
            info = self._environment_provider.inspect_environment(handle)
            self.env_subprocesses[env_hash] = EnvSubprocess(
                info.python_executable, name=env_hash
            )

        return self.env_subprocesses[env_hash]

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

    def _validate_model_supports_task(
        self, model_spec: ModelSpec, task_spec: TaskSpec
    ) -> None:
        model_supported_properties = self._model_registry.get(
            model_spec.kind
        ).supported_properties
        task_required_properties = task_spec.required_model_properties()
        if not task_required_properties.issubset(model_supported_properties):
            raise ValueError(
                f"Model of kind {model_spec.kind} does not support task of kind {task_spec.kind}"
            )

    def _retrieve_environment_and_subprocess(
        self,
        task: TaskSpec,
        model_spec: ModelSpec,
    ) -> tuple[EnvironmentSpec, EnvSubprocess]:
        task_registration = self._task_registry.get(task.kind)
        task_env_spec = task_registration.environment_factory(task)
        env_spec = self.setup_environment(model_spec, task_env_spec)
        env_subprocess = self.get_subprocess(env_spec)
        return env_spec, env_subprocess

    def _retrieve_prepared_model_session(
        self,
        model_spec: ModelSpec,
        task: TaskSpec,
        exec_resources: ExecutionResources,
        env_spec: EnvironmentSpec,
        env_subprocess: EnvSubprocess,
    ) -> PreparedModelSession:
        # Check if we have already prepared this model with the same execution resources
        # in this subprocess, if not prepare it by sending an init_model_request.
        model_cache_key = model_session_key(model_spec, exec_resources)
        env_cache_key = env_spec.short_hash()
        prepared = self.prepared_models.get((model_cache_key, env_cache_key))

        if prepared is None or prepared.process_uuid != env_subprocess.process_uuid:
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
        env_spec, env_subprocess = self._retrieve_environment_and_subprocess(
            task_spec, model_spec
        )

        request = self._prepare_init_model_request(
            model_spec, exec_resources, env_subprocess
        )

        response = self._send_request_and_get_response(env_subprocess, request)

        if response.operation == "error":
            raise RuntimeError(response.error or "Worker returned an unknown error")

        model_session_id = response.model_session_id
        model_cache_key = model_session_key(model_spec, exec_resources)
        env_cache_key = env_spec.short_hash()

        self.prepared_models[(model_cache_key, env_cache_key)] = PreparedModelSession(
            model_spec=model_spec,
            model_session_id=model_session_id,
            execution_resources=exec_resources,
            resolved_resources=response.resolved_resources,
            process_uuid=env_subprocess.process_uuid,
        )

    def execute(
        self,
        task: TaskSpec,
        model: ModelSpec,
        exec_resources: ExecutionResources | None = None,
    ) -> TaskResult:

        if exec_resources is None:
            exec_resources = ExecutionResources()

        # Check that the model can support the task before starting the subprocess
        self._validate_model_supports_task(model, task)

        # Setup / Retrieve the environment and subprocess for this task
        env_spec, env_subprocess = self._retrieve_environment_and_subprocess(
            task, model
        )

        # Check if we have already prepared this model with the same execution resources
        # in this subprocess, if not prepare it by sending an init_model_request.
        prepared = self._retrieve_prepared_model_session(
            model, task, exec_resources, env_spec, env_subprocess
        )

        # Convert to a TaskRequest
        request = TaskRequest(
            operation="task",
            request_id=str(env_subprocess.get_request_counter()),
            model_session_id=prepared.model_session_id,
            task_kind=task.kind,
            task_payload=task.model_dump(),
        )

        # Send the request to the subprocess
        response = self._send_request_and_get_response(env_subprocess, request)

        if response.operation == "error":
            raise RuntimeError(response.error or "Worker returned an unknown error")

        # Convert to a TaskResult of the appropriate type based on the task kind
        registration = self._task_registry.get(response.task_kind)
        result = registration.result_model.model_validate(response.result_payload)

        return result

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
