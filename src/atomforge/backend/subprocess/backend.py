import subprocess
from pathlib import Path

from atomforge.backend.base.session import model_session_key
from atomforge.env.base.env import EnvironmentSpec
from atomforge.env.base.provider import EnvironmentProvider
from atomforge.env.uv import UVEnvironmentProvider
from atomforge.model.base.spec import ModelSpec
from atomforge.model.builtin import get_default_model_registry
from atomforge.task.base.base import Task
from atomforge.task.base.builtin import get_default_task_registry
from atomforge.task.base.resources import ExecutionResources, ResolvedResources
from atomforge.task.base.result import TaskResult

from .core import read_response, write_request
from .request import TaskRequest, ShutdownRequest, RequestMessage, InitModelRequest
from .response import ResponseMessage

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
            [executeable.as_posix(), "-m", "atomforge.backend.subprocess.worker", name],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=None,
            text=True,
        )

        if self._process.stdin is None or self._process.stdout is None:
            raise RuntimeError("Failed to open worker pipes")

        self._stdin = self._process.stdin
        self._stdout = self._process.stdout

    def get_request_counter(self) -> int:
        self._request_counter += 1
        return self._request_counter


class SubprocessBackend:
    def __init__(self, environment_provider: EnvironmentProvider | None = None) -> None:
        self._environment_provider = environment_provider or UVEnvironmentProvider()
        self.env_subprocesses: dict[str, EnvSubprocess] = {}
        self.prepared_models: dict[tuple[str, str], PreparedModelSession] = {}

        self._task_registry = get_default_task_registry()
        self._model_registry = get_default_model_registry()

    def setup_environment(self, model_spec: ModelSpec, task_env_spec: EnvironmentSpec | None) -> EnvironmentSpec:

        # For now, we just use the default environment spec from the model,
        # but in the future we could allow tasks to specify their own environment requirements
        model_env_spec = self._model_registry.get(model_spec.kind).environment_factory(
            model_spec
        )
        # Get the subprocess for the environment
        if task_env_spec is not None:
            env_spec = model_env_spec + task_env_spec
        else:
            env_spec = model_env_spec
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
        
    def prepare_model(self, model_spec: ModelSpec, exec_resources: ExecutionResources, task_env_spec: EnvironmentSpec | None) -> None:
        env_spec = self.setup_environment(model_spec, task_env_spec)
        env_subprocess = self.get_subprocess(env_spec)

        request = InitModelRequest(
            operation="init_model",
            request_id=str(env_subprocess.get_request_counter()),
            model_kind=model_spec.kind,
            model_payload=model_spec.model_dump(),
            exec_resources=exec_resources,
        )

        write_request(env_subprocess._stdin, request)
        response = read_response(env_subprocess._stdout)
        self._ensure_matching_response(request, response)

        if response.operation == "error":
            print(f"Worker error during model initialization: {response.error}", flush=True)
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
        task: Task,
        model_spec: ModelSpec,
        exec_resources: ExecutionResources | None = None,
    ) -> TaskResult:

        if exec_resources is None:
            exec_resources = ExecutionResources()

        # Check that the model can support the task before starting the subprocess
        model_registration = self._model_registry.get(model_spec.kind)
        if not task.required_model_properties.issubset(
            model_registration.supported_properties
        ):
            raise ValueError(
                f"Model of kind {model_spec.kind} does not support task of kind {task.task_name}"
            )

        # Setup / Retrieve the environment and subprocess for this task
        task_env_spec = task.executor_environment()
        env_spec = self.setup_environment(model_spec, task_env_spec)
        env_subprocess = self.get_subprocess(env_spec)

        # Check if we have already prepared this model with the same execution resources
        # in this subprocess, if not prepare it by sending an init_model_request.

        model_cache_key = model_session_key(model_spec, exec_resources)
        env_cache_key = env_spec.short_hash()
        prepared = self.prepared_models.get((model_cache_key, env_cache_key))
        
        if prepared is None or prepared.process_uuid != env_subprocess.process_uuid:
            self.prepared_models.pop((model_cache_key, env_cache_key), None)
            self.prepare_model(model_spec, exec_resources, task_env_spec)
            prepared = self.prepared_models[(model_cache_key, env_cache_key)]

        # Convert to a TaskRequest
        task_spec = task.to_spec()
        request = TaskRequest(
            operation="task",
            request_id=str(env_subprocess.get_request_counter()),
            model_session_id=prepared.model_session_id,
            task_kind=task_spec.kind,
            task_payload=task_spec.model_dump(),
        )

        # Send the request to the subprocess
        write_request(env_subprocess._stdin, request)
        response = read_response(env_subprocess._stdout)
        self._ensure_matching_response(request, response)

        if response.operation == "error":
            print(f"Worker error: {response.error}", flush=True)
            raise RuntimeError(response.error or "Worker returned an unknown error")

        registration = self._task_registry.get(response.task_kind)
        result = registration.result_model.model_validate(response.result_payload)

        return result

    def send_shutdown(self, env_key: str) -> None:
        if env_key in self.env_subprocesses:
            env_subprocess = self.env_subprocesses[env_key]
        else:
            env_subprocess = None

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
            for (model_cache_key, cache_env_key), session in self.prepared_models.items():
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
