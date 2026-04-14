import subprocess
from pathlib import Path

from atomforge.env import EnvironmentProvider, EnvironmentSpec, UVEnvironmentProvider
from atomforge.model import Model
from atomforge.task.base import Task, TaskResult, get_default_task_registry

from .core import read_response, write_request
from .request import TaskRequest, ShutdownRequest, RequestMessage
from .response import ResponseMessage


class EnvSubprocess:
    def __init__(self, executeable: Path, name: str) -> None:
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

        self._registry = get_default_task_registry()

    def setup_environment(self, task: Task, model: Model) -> EnvironmentSpec:
        # For now, we just use the default environment spec from the model,
        # but in the future we could allow tasks to specify their own environment requirements
        model_env_spec = model.default_environment()

        # Get the environment spec from the task, which may extend the model's default environment spec
        task_env_spec = task.executor_environment()

        # Get the subprocess for the environment
        env_spec = model_env_spec + task_env_spec
        return env_spec

    def get_subprocess(self, env_spec: EnvironmentSpec) -> EnvSubprocess:
        name_with_hash = env_spec.name_with_hash()

        if name_with_hash not in self.env_subprocesses:
            handle = self._environment_provider.ensure_environment(env_spec)
            info = self._environment_provider.inspect_environment(handle)
            self.env_subprocesses[name_with_hash] = EnvSubprocess(
                info.python_executable, name=name_with_hash
            )

        return self.env_subprocesses[name_with_hash]

    def _ensure_matching_response(
        self, request: RequestMessage, response: ResponseMessage
    ) -> None:
        if response.request_id != request.request_id:
            raise RuntimeError(
                f"Response id mismatch: expected {request.request_id}, got {response.request_id}"
            )

    def execute(self, task: Task, model: Model) -> TaskResult:
        if not model.supports(*task.required_model_properties):
            raise ValueError(
                f"Model {model.model_kind} does not support required properties for task {task.task_name}: {task.required_model_properties}"
            )

        # Set up the environment and subprocess for this task
        env_spec = self.setup_environment(task, model)
        env_subprocess = self.get_subprocess(env_spec)

        # Convert to a TaskRequest
        task_spec = task.to_spec()
        request = TaskRequest(
            operation="task",
            request_id=str(env_subprocess.get_request_counter()),
            model_kind=model.model_kind,
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

        registration = self._registry.get(response.task_kind)
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
        else:
            print(f"No subprocess found for environment {env_key}, skipping shutdown.")

    def shutdown(self) -> None:
        for env_key in list(self.env_subprocesses.keys()):
            self.send_shutdown(env_key)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()
