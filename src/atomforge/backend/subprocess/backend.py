import subprocess
from pathlib import Path

from atomforge.env import EnvironmentProvider, EnvironmentSpec, UVEnvironmentProvider
from atomforge.model import Model
from atomforge.task.base import Task, TaskResult, get_default_registry

from .core import ComputeRequest, ComputeResponse, read_response, write_request


class EnvSubprocess:
    def __init__(self, executeable: Path):
        self._request_counter = 0
        self._process = subprocess.Popen(
            [executeable.as_posix(), "-m", "atomforge.backend.subprocess.worker"],
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

        self._registry = get_default_registry()

    def get_subprocess(self, env_spec: EnvironmentSpec) -> EnvSubprocess:
        name_with_hash = env_spec.name_with_hash()

        if name_with_hash not in self.env_subprocesses:
            handle = self._environment_provider.ensure_environment(env_spec)
            info = self._environment_provider.inspect_environment(handle)
            self.env_subprocesses[name_with_hash] = EnvSubprocess(
                info.python_executable
            )

        return self.env_subprocesses[name_with_hash]

    def _ensure_matching_response(
        self, request: ComputeRequest, response: ComputeResponse
    ) -> None:
        if response.request_id != request.request_id:
            raise RuntimeError(
                f"Response id mismatch: expected {request.request_id}, got {response.request_id}"
            )

    def execute(self, task: Task, model: Model) -> TaskResult:
        # For now, we just use the default environment spec from the model,
        # but in the future we could allow tasks to specify their own environment requirements
        env_spec = model.default_environment()

        # Get the subprocess for the environment
        env_subprocess = self.get_subprocess(env_spec)

        # For now only support SinglePoint-task
        if task.task_name != "single_point":
            raise NotImplementedError(
                f"Task {task.task_name} is not supported by the subprocess backend"
            )

        # Convert to a ComputeRequest

        task_spec = task.to_spec()

        request = ComputeRequest(
            operation="task",
            request_id=str(env_subprocess.get_request_counter()),
            model_name=model.model_name,
            task_kind=task_spec.kind,
            task_payload=task_spec.model_dump(),
        )

        # Send the request to the subprocess
        write_request(env_subprocess._stdin, request)
        response = read_response(env_subprocess._stdout)
        self._ensure_matching_response(request, response)

        if not response.ok:
            print(f"Worker error: {response.error}", flush=True)
            raise RuntimeError(response.error or "Worker returned an unknown error")
        
        registration = self._registry.get(response.task_kind)
        result = registration.result_model.model_validate(response.result_payload)

        return result
