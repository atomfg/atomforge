from typing import Literal

from pydantic import BaseModel

from atomforge_core.provenance import (
    EnvironmentProvenance,
    ExecutionProvenance,
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
