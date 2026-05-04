from datetime import datetime
from importlib.metadata import PackageNotFoundError, version

from atomforge_core.model.spec import ModelSpec
from atomforge_core.provenance import (
    EnvironmentProvenance,
    ExecutionProvenance,
    ModelProvenance,
    PartialProvenance,
    Provenance,
    ResourceProvenance,
    TaskProvenance,
    payload_hash,
)
from atomforge_core.resources.resource_models import (
    ExecutionResources,
    ResolvedResources,
)
from atomforge_core.task.result import TaskResult
from atomforge_core.task.spec import TaskSpec
from atomforge_runtime.registry.model.model_registry import ModelRegistry


def distribution_versions(distributions: list[str]) -> dict[str, str]:
    versions = {}
    for distribution in distributions:
        try:
            versions[distribution] = version(distribution)
        except PackageNotFoundError:
            continue
    return versions


def build_model_provenance(
    model: ModelSpec | None,
    model_registry: ModelRegistry,
) -> ModelProvenance | None:
    if model is None or not isinstance(model, ModelSpec):
        return None

    model_registration = model_registry.get(model.kind)
    distributions = tuple(model_registration.source)
    return ModelProvenance(
        kind=model.kind,
        payload_hash=payload_hash(model),
        distributions=distributions,
        versions=distribution_versions(list(distributions)),
    )


def build_provenance(
    *,
    task: TaskSpec,
    model: ModelSpec | None,
    model_registry: ModelRegistry,
    environment_provenance: EnvironmentProvenance,
    exec_resources: ExecutionResources,
    resolved_resources: ResolvedResources | None,
    started_at: datetime,
    ended_at: datetime,
    wall_time_s: float,
) -> Provenance:
    model_provenance = build_model_provenance(model, model_registry)

    return Provenance(
        task=TaskProvenance(
            kind=task.kind,
            payload_hash=payload_hash(task),
        ),
        model=model_provenance,
        environment=environment_provenance,
        resources=ResourceProvenance(
            requested=exec_resources,
            resolved=resolved_resources,
        ),
        execution=ExecutionProvenance(
            backend="subprocess",
            started_at=started_at,
            ended_at=ended_at,
            wall_time_s=wall_time_s,
        ),
    )


def build_partial_provenance(
    *,
    task: TaskSpec,
    model: ModelSpec | None,
    model_registry: ModelRegistry,
    exec_resources: ExecutionResources,
    resolved_resources: ResolvedResources | None,
    started_at: datetime,
    ended_at: datetime,
    wall_time_s: float,
    environment_provider: str | None = None,
    environment_key: str | None = None,
    environment_spec_hash: str | None = None,
) -> PartialProvenance:
    return PartialProvenance(
        task=TaskProvenance(
            kind=task.kind,
            payload_hash=payload_hash(task),
        ),
        model=build_model_provenance(model, model_registry),
        resources=ResourceProvenance(
            requested=exec_resources,
            resolved=resolved_resources,
        ),
        execution=ExecutionProvenance(
            backend="subprocess",
            started_at=started_at,
            ended_at=ended_at,
            wall_time_s=wall_time_s,
        ),
        environment_provider=environment_provider,
        environment_key=environment_key,
        environment_spec_hash=environment_spec_hash,
    )


def attach_provenance(result: TaskResult, provenance: Provenance) -> TaskResult:
    if isinstance(result, TaskResult):
        return result.model_copy(update={"provenance": provenance})
    setattr(result, "provenance", provenance)
    return result
