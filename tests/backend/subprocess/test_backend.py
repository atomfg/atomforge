import pytest
from unittest.mock import Mock
from atomforge.backend.subprocess.backend import (
    PreparedEnvironmentSession,
    PreparedModelSession,
    SubprocessBackend,
)
from atomforge_core.env.env import EnvironmentSpec
from atomforge.env.base.handle import EnvironmentHandle
from atomforge.env.base.info import EnvironmentInfo
from atomforge_core.model.spec import ModelSpec
from atomforge_core.protocol.response import ShutdownResponse
from atomforge_core.protocol.request import ShutdownRequest
from atomforge_core.provenance import EnvironmentProvenance, payload_hash
from atomforge_core.resources.resource_models import ExecutionResources, ResolvedResources
from atomforge_core.task.result import TaskResult
from atomforge_core.task.spec import TaskSpec


class TaskOnlySpec(TaskSpec):
    requires_model = False
    kind: str = "task-only"
    value: int = 1

    def required_model_properties(self):
        return frozenset()


class TaskOnlyResult(TaskResult):
    kind: str
    doubled_value: int
    used_model: bool
    resource_accelerator: str | None


class ModelTaskSpec(TaskSpec):
    kind: str = "model-task"
    value: int = 1

    def required_model_properties(self):
        return frozenset()


class ModelTaskResult(TaskResult):
    kind: str
    value: int


class FakeModel(ModelSpec):
    kind: str = "fake-model"


def make_environment_session(
    env_spec: EnvironmentSpec,
    env_subprocess,
    environment_provenance: EnvironmentProvenance | None = None,
) -> PreparedEnvironmentSession:
    if environment_provenance is None:
        environment_provenance = EnvironmentProvenance(
            provider="uv",
            key="test-env-key",
            spec_hash=env_spec.hash(),
            python=env_spec.python,
            requirements=env_spec.requirements,
            provider_requirements=env_spec.provider_requirements,
        )

    return PreparedEnvironmentSession(
        env_spec=env_spec,
        env_key=environment_provenance.key,
        env_subprocess=env_subprocess,
        environment_provenance=environment_provenance,
    )


@pytest.fixture
def backend():
    return SubprocessBackend()

def test_ensure_matching_request_id(backend):
    request = ShutdownRequest(request_id="test123")
    response = ShutdownResponse(request_id=request.request_id)
    backend._ensure_matching_response(request, response)  # Should not raise

def test_ensure_matching_request_id_mismatch(backend):
    request = ShutdownRequest(request_id="test123")
    response = ShutdownResponse(request_id="different_id")
    with pytest.raises(RuntimeError):
        backend._ensure_matching_response(request, response)

def test_backend_context_manager(backend):
    with backend:
        assert True


def test_get_environment_session_caches_provider_provenance(backend, mocker, tmp_path):
    env_spec = EnvironmentSpec(name="cached-env")
    env_key = backend._environment_provider.environment_key(env_spec)
    handle = EnvironmentHandle(name="cached-env", provider="uv", path=tmp_path)
    info = EnvironmentInfo(
        handle=handle,
        path=tmp_path,
        python_executable=tmp_path / ".venv" / "bin" / "python",
    )
    environment_provenance = EnvironmentProvenance(
        provider="uv",
        key=env_key,
        spec_hash=env_spec.hash(),
    )
    env_subprocess = mocker.Mock()

    ensure_environment = mocker.patch.object(
        backend._environment_provider,
        "ensure_environment",
        return_value=handle,
    )
    inspect_environment = mocker.patch.object(
        backend._environment_provider,
        "inspect_environment",
        return_value=info,
    )
    build_provenance = mocker.patch.object(
        backend._environment_provider,
        "build_provenance",
        return_value=environment_provenance,
    )
    env_subprocess_cls = mocker.patch(
        "atomforge.backend.subprocess.backend.EnvSubprocess",
        return_value=env_subprocess,
    )

    first = backend.get_environment_session(env_spec)
    second = backend.get_environment_session(env_spec)

    assert first is second
    assert first.environment_provenance == environment_provenance
    assert first.env_subprocess == env_subprocess
    assert backend.prepared_environments[env_key] is first
    assert backend.env_subprocesses[env_key] == env_subprocess
    ensure_environment.assert_called_once_with(env_spec)
    inspect_environment.assert_called_once_with(handle)
    build_provenance.assert_called_once_with(env_spec, handle)
    env_subprocess_cls.assert_called_once_with(info.python_executable, name=env_key)


def test_prepare_model_error(backend, mocker):

    class MockResponse:
        def __init__(self, operation):
            self.operation = operation
            self.error = "Model preparation failed"

    mocker.patch(
        "atomforge.backend.subprocess.backend.SubprocessBackend._retrieve_environment_session",
        return_value=Mock(env_subprocess=None, env_key="env-key"),
    )
    mocker.patch("atomforge.backend.subprocess.backend.SubprocessBackend._prepare_init_model_request", return_value=None)
    mocker.patch("atomforge.backend.subprocess.backend.SubprocessBackend._send_request_and_get_response", return_value=MockResponse(operation="error"))

    with pytest.raises(RuntimeError, match="Model preparation failed"):
        backend.prepare_model(model_spec=None, task_spec=None, exec_resources=None)

def test_validate_task_executability(backend, example_structure):
    from atomforge_builtins.model.ase_lj import LennardJones
    from atomforge_builtins.task.single_point import SinglePoint

    model_spec = LennardJones()
    task_spec = SinglePoint(structure=example_structure)
    backend._validate_task_executability(model_spec, task_spec)  # Should not raise


def test_validate_task_executability_unsupported(backend):
    from atomforge_builtins.model.ase_lj import LennardJones
    from atomforge_core.task.spec import TaskSpec
    from atomforge_core.property import Property
    from atomforge_core.registry.symbol_path import SymbolPath
    from atomforge_runtime.registry.task.task_registration import TaskRegistration

    class UnsupportedTaskSpec(TaskSpec):

        kind: str = "unsupported_task"

        def required_model_properties(self) -> frozenset[Property]:
            return frozenset({Property.STRESS})

    backend._task_registry._register(
        TaskRegistration(
            kind="unsupported_task",
            spec_model=UnsupportedTaskSpec,
            result_model_path=SymbolPath("runtime_fakes:FakeTaskResult"),
            executor_class_path=None,
            capability_spec_path=SymbolPath("runtime_fakes:FakeCapabilitySpec"),
            environment_factory_path=SymbolPath("runtime_fakes:FakeEnvironmentFactory"),
            source=["runtime-test-plugin"],
        ),
        "unsupported_task",
    )

    model_spec = LennardJones()
    task_spec = UnsupportedTaskSpec()

    with pytest.raises(ValueError, match="required properties"):
        backend._validate_task_executability(model_spec, task_spec)


def test_validate_task_executability_model_free(backend):
    registration = Mock()
    registration.has_default_executor.return_value = True
    backend._task_registry.get = Mock(return_value=registration)
    task_spec = TaskOnlySpec(value=5)
    backend._validate_task_executability(None, task_spec)


def test_execute_model_free_does_not_prepare_model(backend, mocker):
    task = TaskOnlySpec(value=9)
    env_spec = EnvironmentSpec(name="task-only-env")

    mock_env_subprocess = mocker.Mock()
    mock_env_subprocess.get_request_counter.side_effect = [1]
    registration = mocker.Mock()
    registration.has_default_executor.return_value = True
    registration.load_result_model.return_value = TaskOnlyResult
    backend._task_registry.get = mocker.Mock(return_value=registration)
    mocker.patch(
        "atomforge.backend.subprocess.backend.SubprocessBackend._retrieve_environment_session",
        return_value=make_environment_session(env_spec, mock_env_subprocess),
    )
    prepare_model = mocker.patch(
        "atomforge.backend.subprocess.backend.SubprocessBackend._retrieve_prepared_model_session"
    )

    class MockResponse:
        operation = "task"
        task_kind = "fake-task-only"
        request_id = "1"
        result_payload = {
            "kind": "fake-task-only",
            "doubled_value": 18,
            "used_model": False,
            "resource_accelerator": None,
        }

    mocker.patch(
        "atomforge.backend.subprocess.backend.SubprocessBackend._send_request_and_get_response",
        return_value=MockResponse(),
    )

    result = backend.execute(task)

    prepare_model.assert_not_called()
    assert result.doubled_value == 18


def test_execute_model_free_attaches_provenance(backend, mocker):
    task = TaskOnlySpec(value=9)
    env_spec = EnvironmentSpec(
        name="task-only-env",
        python="3.12",
        requirements=["fake-base"],
        provider_requirements=["runtime-test-plugin"],
    )

    environment_provenance = EnvironmentProvenance(
        provider="uv",
        key="provider-env-key",
        spec_hash=env_spec.hash(),
        python=env_spec.python,
        requirements=env_spec.requirements,
        provider_requirements=env_spec.provider_requirements,
        pyproject_hash="pyproject-hash",
        lockfile_hash="lockfile-hash",
    )
    mock_env_subprocess = mocker.Mock()
    mock_env_subprocess.get_request_counter.side_effect = [1]
    registration = mocker.Mock()
    registration.has_default_executor.return_value = True
    registration.load_result_model.return_value = TaskOnlyResult
    backend._task_registry.get = mocker.Mock(return_value=registration)
    mocker.patch(
        "atomforge.backend.subprocess.backend.SubprocessBackend._retrieve_environment_session",
        return_value=make_environment_session(
            env_spec,
            mock_env_subprocess,
            environment_provenance,
        ),
    )
    mocker.patch(
        "atomforge.backend.subprocess.backend.SubprocessBackend._retrieve_prepared_model_session"
    )

    class MockResponse:
        operation = "task"
        task_kind = "fake-task-only"
        request_id = "1"
        result_payload = {
            "kind": "fake-task-only",
            "doubled_value": 18,
            "used_model": False,
            "resource_accelerator": None,
        }

    mocker.patch(
        "atomforge.backend.subprocess.backend.SubprocessBackend._send_request_and_get_response",
        return_value=MockResponse(),
    )

    result = backend.execute(task)

    assert result.provenance is not None
    assert result.provenance.task.kind == task.kind
    assert result.provenance.task.payload_hash == payload_hash(task)
    assert result.provenance.model is None
    assert result.provenance.environment == environment_provenance
    assert result.provenance.resources.requested == ExecutionResources()
    assert result.provenance.resources.resolved is None
    assert result.provenance.execution.wall_time_s >= 0


def test_execute_model_task_attaches_model_provenance(backend, mocker):
    task = ModelTaskSpec(value=7)
    model = FakeModel()
    exec_resources = ExecutionResources(accelerator="cpu", precision="f64")
    resolved_resources = ResolvedResources(accelerator="cpu", precision="f64")
    env_spec = EnvironmentSpec(
        name="model-env",
        python="3.12",
        requirements=["fake-base"],
        provider_requirements=["runtime-test-plugin"],
    )

    environment_provenance = EnvironmentProvenance(
        provider="uv",
        key="provider-env-key",
        spec_hash=env_spec.hash(),
        python=env_spec.python,
        requirements=env_spec.requirements,
        provider_requirements=env_spec.provider_requirements,
        pyproject_hash="pyproject-hash",
        lockfile_hash="lockfile-hash",
    )
    mock_env_subprocess = mocker.Mock()
    mock_env_subprocess.process_uuid = "process-uuid"
    mock_env_subprocess.get_request_counter.side_effect = [1]
    registration = mocker.Mock()
    registration.load_result_model.return_value = ModelTaskResult
    backend._task_registry.get = mocker.Mock(return_value=registration)
    backend._model_registry.get = mocker.Mock(
        return_value=Mock(source=["runtime-test-plugin"])
    )
    mocker.patch.object(backend, "_validate_task_executability")
    mocker.patch(
        "atomforge.backend.subprocess.backend.SubprocessBackend._retrieve_environment_session",
        return_value=make_environment_session(
            env_spec,
            mock_env_subprocess,
            environment_provenance,
        ),
    )
    mocker.patch(
        "atomforge.backend.subprocess.backend.SubprocessBackend._retrieve_prepared_model_session",
        return_value=PreparedModelSession(
            model_spec=model,
            model_session_id="model-session",
            execution_resources=exec_resources,
            resolved_resources=resolved_resources,
            process_uuid=mock_env_subprocess.process_uuid,
        ),
    )

    class MockResponse:
        operation = "task"
        task_kind = "model-task"
        request_id = "1"
        result_payload = {"kind": "model-task", "value": 14}

    mocker.patch(
        "atomforge.backend.subprocess.backend.SubprocessBackend._send_request_and_get_response",
        return_value=MockResponse(),
    )

    result = backend.execute(task, model=model, exec_resources=exec_resources)

    assert result.provenance is not None
    assert result.provenance.task.kind == task.kind
    assert result.provenance.task.payload_hash == payload_hash(task)
    assert result.provenance.model is not None
    assert result.provenance.model.kind == model.kind
    assert result.provenance.model.payload_hash == payload_hash(model)
    assert result.provenance.model.distributions == ("runtime-test-plugin",)
    assert result.provenance.model.versions == {}
    assert result.provenance.environment == environment_provenance
    assert result.provenance.resources.requested == exec_resources
    assert result.provenance.resources.resolved == resolved_resources
    assert result.provenance.execution.wall_time_s >= 0


def test_execute_model_free_rejects_model_argument(backend):
    task = TaskOnlySpec(value=9)

    with pytest.raises(ValueError, match="model-free"):
        backend.execute(task, model=object())
