from atomforge_core.protocol.request import ShutdownRequest
from atomforge_core.protocol.response import ShutdownResponse


def test_worker_run(run_worker):
    exit_code, stdout, stderr = run_worker("")
    assert exit_code == 0


def test_worker_run_invalid_request(run_worker):
    exit_code, stdout, stderr = run_worker("invalid request")
    assert exit_code == 1
    assert "invalid request" in stderr


def test_worker_run_shutdown(run_worker):
    request = ShutdownRequest(request_id="test_request_id")
    request_json = request.model_dump_json()
    exit_code, stdout, stderr = run_worker(request_json)
    assert exit_code == 0
    response = ShutdownResponse.model_validate_json(stdout)
    assert response.request_id == "test_request_id"

