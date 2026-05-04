from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Literal

from atomforge.backend.subprocess._provenance import (
    attach_provenance,
    build_partial_provenance,
    build_provenance,
)
from atomforge_core.env.env import EnvironmentSpec
from atomforge_core.model.spec import ModelSpec
from atomforge_core.provenance import ExecutionErrorRecord, ExecutionRecord
from atomforge_core.resources.resource_models import ExecutionResources, ResolvedResources
from atomforge_core.task.result import TaskResult
from atomforge_core.task.spec import TaskSpec

if TYPE_CHECKING:
    from atomforge.backend.subprocess._environment import PreparedEnvironmentSession
    from atomforge.backend.subprocess.backend import SubprocessBackend


def end_timing(started_perf: float) -> tuple[datetime, float]:
    return datetime.now(timezone.utc), time.perf_counter() - started_perf


def error_from_exception(exc: Exception) -> ExecutionErrorRecord:
    return ExecutionErrorRecord(
        error_type=exc.__class__.__name__,
        message=str(exc) or exc.__class__.__name__,
    )


def error_from_worker(response) -> ExecutionErrorRecord:
    return ExecutionErrorRecord(
        error_type="WorkerError",
        message=response.error or "Worker returned an unknown error",
        worker_traceback=getattr(response, "traceback", None),
    )


@dataclass
class ExecutionAttempt:
    backend: SubprocessBackend
    task: TaskSpec
    model: ModelSpec | None
    exec_resources: ExecutionResources
    started_at: datetime
    started_perf: float

    def input_error(self, message: str) -> ExecutionRecord:
        return self.partial_record(
            status="error",
            phase="input_validation",
            error=ExecutionErrorRecord(error_type="ValueError", message=message),
        )

    def partial_record(
        self,
        *,
        status: Literal["error", "incompatibility"],
        phase: Literal[
            "input_validation",
            "environment_preparation",
            "model_preparation",
            "task_execution",
            "result_validation",
        ],
        error: ExecutionErrorRecord,
        resolved_resources: ResolvedResources | None = None,
        env_session: PreparedEnvironmentSession | None = None,
        env_spec: EnvironmentSpec | None = None,
    ) -> ExecutionRecord:
        ended_at, wall_time_s = end_timing(self.started_perf)
        environment_provider = None
        environment_key = None
        environment_spec_hash = None
        if env_session is not None:
            environment_provider = env_session.environment_provenance.provider
            environment_key = env_session.env_key
            environment_spec_hash = env_session.env_spec.hash()
        elif env_spec is not None:
            environment_provider = self.backend._environment_provider.provider_name
            environment_key = self.backend._environment_provider.environment_key(
                env_spec
            )
            environment_spec_hash = env_spec.hash()

        partial = build_partial_provenance(
            task=self.task,
            model=self.model,
            model_registry=self.backend._model_registry,
            exec_resources=self.exec_resources,
            resolved_resources=resolved_resources,
            started_at=self.started_at,
            ended_at=ended_at,
            wall_time_s=wall_time_s,
            environment_provider=environment_provider,
            environment_key=environment_key,
            environment_spec_hash=environment_spec_hash,
        )
        return ExecutionRecord(
            status=status,
            phase=phase,
            partial_provenance=partial,
            error=error,
        )

    def full_provenance(
        self,
        *,
        env_session: PreparedEnvironmentSession,
        resolved_resources: ResolvedResources | None,
        ended_at: datetime,
        wall_time_s: float,
    ):
        return build_provenance(
            task=self.task,
            model=self.model,
            model_registry=self.backend._model_registry,
            environment_provenance=env_session.environment_provenance,
            exec_resources=self.exec_resources,
            resolved_resources=resolved_resources,
            started_at=self.started_at,
            ended_at=ended_at,
            wall_time_s=wall_time_s,
        )

    def full_error_record(
        self,
        *,
        status: Literal["error", "incompatibility"],
        phase: Literal["task_execution", "result_validation"],
        env_session: PreparedEnvironmentSession,
        resolved_resources: ResolvedResources | None,
        ended_at: datetime,
        wall_time_s: float,
        error: ExecutionErrorRecord,
    ) -> ExecutionRecord:
        return ExecutionRecord(
            status=status,
            phase=phase,
            provenance=self.full_provenance(
                env_session=env_session,
                resolved_resources=resolved_resources,
                ended_at=ended_at,
                wall_time_s=wall_time_s,
            ),
            error=error,
        )

    def success_record(
        self,
        *,
        result: TaskResult,
        env_session: PreparedEnvironmentSession,
        resolved_resources: ResolvedResources | None,
        ended_at: datetime,
        wall_time_s: float,
    ) -> ExecutionRecord:
        provenance = self.full_provenance(
            env_session=env_session,
            resolved_resources=resolved_resources,
            ended_at=ended_at,
            wall_time_s=wall_time_s,
        )
        return ExecutionRecord(
            status="success",
            phase="task_execution",
            result=attach_provenance(result, provenance),
            provenance=provenance,
        )
