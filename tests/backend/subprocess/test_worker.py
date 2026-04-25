import pytest
from atomforge_core.structure import StructureData
from atomforge_builtins.model.nodep_model import NoDep
from atomforge_builtins.task.singlepoint import SinglePoint

from atomforge_core.protocol.request import (
    InitModelRequest,
    TaskRequest,
    ShutdownRequest,
)
from atomforge_core.protocol.response import (
    InitModelResponse,
    TaskResponse,
    ShutdownResponse,
    ErrorResponse,
)
from atomforge_core.resources.resource_models import ExecutionResources


@pytest.fixture(scope="module")
def init_model_response(worker):
    spec = NoDep()
    exec_resoruces = ExecutionResources()
    request = InitModelRequest(
        request_id="test_request_1",
        model_kind=spec.kind,
        model_payload=spec.model_dump(),
        exec_resources=exec_resoruces,
    )
    response, should_exit = worker._handle_request(request)
    return response, should_exit

@pytest.fixture(scope="module")
def malformed_init_model_response(worker):
    request = InitModelRequest(
        request_id="test_request_1",
        model_kind="unknown_model",
        model_payload={},
        exec_resources=ExecutionResources(),
    )
    response, should_exit = worker._handle_request(request)
    return response, should_exit


@pytest.fixture(scope="module")
def task_request_response(worker, init_model_response):

    structure = StructureData(
        positions=[[0, 0, 0], [1, 0, 0]],
        cell=[[10, 0, 0], [0, 10, 0], [0, 0, 10]],
        numbers=[18, 18],
        pbc=[False, False, False],
    )

    task = SinglePoint(structure=structure)

    task_request = TaskRequest(
        request_id="test_request_2",
        model_session_id=init_model_response[0].model_session_id,
        task_kind="single_point",
        task_payload=task.model_dump(),
    )

    response, should_exit = worker._handle_request(task_request)
    return response, should_exit


@pytest.fixture(scope="module")
def malformed_task_request_response(worker, init_model_response):

    task_request = TaskRequest(
        request_id="test_request_4",
        model_session_id=init_model_response[0].model_session_id,
        task_kind="single_point",
        task_payload={"invalid": "payload"},
    )

    response, should_exit = worker._handle_request(task_request)
    return response, should_exit

@pytest.fixture(scope="module")
def unknown_operation_request_response(worker):

    class UnknownRequest:
        def __init__(self):
            self.request_id = "test_request_5"
            self.operation = "unknown_operation"        

    response, should_exit = worker._handle_request(UnknownRequest())
    return response, should_exit

@pytest.fixture(scope="module")
def shutdown_response(worker):
    request = ShutdownRequest(request_id="test_request_3")
    response, should_exit = worker._handle_request(request)
    return response, should_exit


def test_worker_initialization(worker):
    assert worker._name == "test_worker"
    assert worker._task_registry is not None
    assert worker._model_registry is not None
    assert worker._system_resources is not None


def test_init_model_request_response(init_model_response):
    response, _ = init_model_response
    assert isinstance(response, InitModelResponse)


def test_init_model_request_should_exit(init_model_response):
    _, should_exit = init_model_response
    assert not should_exit


def test_init_model_request(worker, init_model_response):
    response, _ = init_model_response
    assert response.model_session_id is not None
    assert response.model_session_id in worker._model_sessions

def test_malformed_init_model_request_response(malformed_init_model_response):
    response, _ = malformed_init_model_response
    assert isinstance(response, ErrorResponse)

def test_task_request_response(task_request_response):
    response, _ = task_request_response
    assert isinstance(response, TaskResponse)

def test_task_request_should_exit(task_request_response):
    _, should_exit = task_request_response
    assert not should_exit

def test_task_request_result(task_request_response):
    response, _ = task_request_response
    assert "energy" in response.result_payload

def test_shutdown_request_response(shutdown_response):
    response, _ = shutdown_response
    assert isinstance(response, ShutdownResponse)

def test_shutdown_request_should_exit(shutdown_response):
    _, should_exit = shutdown_response
    assert should_exit

def test_malformed_task_request_response(malformed_task_request_response):
    response, _ = malformed_task_request_response
    assert isinstance(response, ErrorResponse)

def test_malformed_task_request_should_exit(malformed_task_request_response):
    _, should_exit = malformed_task_request_response
    assert not should_exit

def test_unknown_operation_request_response(unknown_operation_request_response):
    response, _ = unknown_operation_request_response
    assert isinstance(response, ErrorResponse)
