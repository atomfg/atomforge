from typing import Literal

from pydantic import BaseModel

from atomforge_core.provenance import (
    EnvironmentProvenance,
    ExecutionErrorRecord,
    ExecutionRecord,
    ExecutionProvenance,
    PartialProvenance,
    Provenance,
    ResourceProvenance,
    TaskProvenance,
    payload_hash,
)
from atomforge_core.resources.resource_models import ExecutionResources
from atomforge_core.task.result import TaskResult


class ExampleResult(TaskResult):
    kind: Literal["example"] = "example"
    value: int


class SetPayload(BaseModel):
    values: frozenset[str]


def test_payload_hash_is_stable_for_equivalent_pydantic_payloads():
    first = ExecutionResources(accelerator="cpu", precision="f64")
    second = ExecutionResources(precision="f64", accelerator="cpu")

    assert payload_hash(first) == payload_hash(second)


def test_payload_hash_is_stable_for_set_ordering():
    first = SetPayload(values=frozenset({"b", "a"}))
    second = SetPayload(values=frozenset({"a", "b"}))

    assert payload_hash(first) == payload_hash(second)


def test_provenance_validates_with_minimal_fields():
    provenance = Provenance(
        task=TaskProvenance(kind="example", payload_hash="task-hash"),
        environment=EnvironmentProvenance(
            provider="uv",
            key="env-key",
            spec_hash="env-hash",
        ),
        resources=ResourceProvenance(requested=ExecutionResources()),
        execution=ExecutionProvenance(
            backend="subprocess",
            started_at="2026-05-04T10:00:00Z",
            ended_at="2026-05-04T10:00:01Z",
            wall_time_s=1.0,
        ),
    )

    assert provenance.task.kind == "example"
    assert provenance.model is None
    assert provenance.environment.pyproject_hash is None
    assert provenance.environment.lockfile_hash is None


def test_task_result_accepts_no_provenance():
    result = ExampleResult(value=1)

    assert result.provenance is None
    assert result.model_dump() == {"kind": "example", "value": 1}


def test_task_result_accepts_provenance():
    provenance = Provenance(
        task=TaskProvenance(kind="example", payload_hash="task-hash"),
        environment=EnvironmentProvenance(
            provider="uv",
            key="env-key",
            spec_hash="env-hash",
        ),
        resources=ResourceProvenance(requested=ExecutionResources()),
        execution=ExecutionProvenance(
            backend="subprocess",
            started_at="2026-05-04T10:00:00Z",
            ended_at="2026-05-04T10:00:01Z",
            wall_time_s=1.0,
        ),
    )

    result = ExampleResult(value=1, provenance=provenance)

    assert result.provenance == provenance
    assert result.model_dump()["provenance"] == provenance.model_dump()


def test_execution_record_validates_success_with_typed_result():
    provenance = Provenance(
        task=TaskProvenance(kind="example", payload_hash="task-hash"),
        environment=EnvironmentProvenance(
            provider="uv",
            key="env-key",
            spec_hash="env-hash",
        ),
        resources=ResourceProvenance(requested=ExecutionResources()),
        execution=ExecutionProvenance(
            backend="subprocess",
            started_at="2026-05-04T10:00:00Z",
            ended_at="2026-05-04T10:00:01Z",
            wall_time_s=1.0,
        ),
    )
    result = ExampleResult(value=1, provenance=provenance)

    record = ExecutionRecord(
        status="success",
        phase="task_execution",
        result=result,
        provenance=provenance,
    )

    assert record.result == result
    assert record.provenance == provenance
    assert record.error is None


def test_execution_record_validates_error_with_partial_provenance():
    partial = PartialProvenance(
        task=TaskProvenance(kind="example", payload_hash="task-hash"),
        resources=ResourceProvenance(requested=ExecutionResources()),
        execution=ExecutionProvenance(
            backend="subprocess",
            started_at="2026-05-04T10:00:00Z",
            ended_at="2026-05-04T10:00:01Z",
            wall_time_s=1.0,
        ),
        environment_provider="uv",
        environment_key="env-key",
        environment_spec_hash="env-hash",
    )

    record = ExecutionRecord(
        status="error",
        phase="environment_preparation",
        partial_provenance=partial,
        error=ExecutionErrorRecord(
            error_type="RuntimeError",
            message="environment failed",
        ),
    )

    assert record.result is None
    assert record.provenance is None
    assert record.partial_provenance == partial


def test_execution_record_validates_incompatibility():
    partial = PartialProvenance(
        task=TaskProvenance(kind="example", payload_hash="task-hash"),
        resources=ResourceProvenance(requested=ExecutionResources()),
        execution=ExecutionProvenance(
            backend="subprocess",
            started_at="2026-05-04T10:00:00Z",
            ended_at="2026-05-04T10:00:01Z",
            wall_time_s=1.0,
        ),
    )

    record = ExecutionRecord(
        status="incompatibility",
        phase="input_validation",
        partial_provenance=partial,
        error=ExecutionErrorRecord(
            error_type="Incompatibility",
            message="unsupported",
        ),
    )

    assert record.status == "incompatibility"
    assert record.error.message == "unsupported"


def test_execution_error_record_accepts_worker_traceback():
    error = ExecutionErrorRecord(
        error_type="WorkerError",
        message="task failed",
        worker_traceback="Traceback text",
    )

    assert error.worker_traceback == "Traceback text"
