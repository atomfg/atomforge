import pytest
from atomforge.backend.subprocess.backend import SubprocessBackend
from atomforge_core.protocol.response import ShutdownResponse
from atomforge_core.protocol.request import ShutdownRequest

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

def test_validate_model_supports_task(backend, example_structure):
    from atomforge_builtins.model.ase_lj import LennardJones
    from atomforge_builtins.task.singlepoint import SinglePoint

    model_spec = LennardJones()
    task_spec = SinglePoint(structure=example_structure)
    backend._validate_model_supports_task(model_spec, task_spec) # Should not raise

def test_validate_model_supports_task_unsupported(backend):
    from atomforge_builtins.model.ase_lj import LennardJones
    from atomforge_core.task.spec import TaskSpec
    from atomforge_core.property import Property

    class UnsupportedTaskSpec(TaskSpec):

        kind: str = "unsupported_task"

        def required_model_properties(self) -> frozenset[Property]:
            return frozenset("ImaginaryProperty")

    model_spec = LennardJones()
    task_spec = UnsupportedTaskSpec()

    with pytest.raises(ValueError, match="Model of kind ase-lj does not support task of kind unsupported_task"):
        backend._validate_model_supports_task(model_spec, task_spec)



