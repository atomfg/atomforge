import pytest
from unittest.mock import Mock
from atomforge.backend.subprocess.backend import SubprocessBackend
from atomforge_core.protocol.response import ShutdownResponse
from atomforge_core.protocol.request import ShutdownRequest
from atomforge_core.task.spec import TaskSpec


class TaskOnlySpec(TaskSpec):
    requires_model = False
    kind: str = "task-only"
    value: int = 1

    def required_model_properties(self):
        return frozenset()


class TaskOnlyResult:
    @classmethod
    def model_validate(cls, payload):
        result = cls()
        result.kind = payload["kind"]
        result.doubled_value = payload["doubled_value"]
        result.used_model = payload["used_model"]
        result.resource_accelerator = payload["resource_accelerator"]
        return result

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

def test_prepare_model_error(backend, mocker):

    class MockResponse:
        def __init__(self, operation):
            self.operation = operation
            self.error = "Model preparation failed"

    mocker.patch("atomforge.backend.subprocess.backend.SubprocessBackend._retrieve_environment_and_subprocess", return_value=(None, None))
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

    mock_env_subprocess = mocker.Mock()
    mock_env_subprocess.get_request_counter.side_effect = [1]
    registration = mocker.Mock()
    registration.has_default_executor.return_value = True
    registration.load_result_model.return_value = TaskOnlyResult
    backend._task_registry.get = mocker.Mock(return_value=registration)
    mocker.patch(
        "atomforge.backend.subprocess.backend.SubprocessBackend._retrieve_environment_and_subprocess",
        return_value=(None, mock_env_subprocess),
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


def test_execute_model_free_rejects_model_argument(backend):
    task = TaskOnlySpec(value=9)

    with pytest.raises(ValueError, match="model-free"):
        backend.execute(task, model=object())
