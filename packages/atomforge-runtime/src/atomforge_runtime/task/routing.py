from __future__ import annotations

from atomforge_core.task.executability import ExecutionRoute, RouteKind
from atomforge_core.task.execution_policy import ExecutionPolicy
from atomforge_core.task.spec import TaskSpec
from atomforge_runtime.registry.model.model_registration import ModelRegistration
from atomforge_runtime.registry.task.task_registration import TaskRegistration


def resolve_candidate_routes(
    task_spec: TaskSpec,
    task_registration: TaskRegistration,
    model_registration: ModelRegistration | None,
) -> tuple[ExecutionRoute, ...]:
    policy = task_spec.execution_policy
    has_default = task_registration.has_default_executor()
    routes: list[ExecutionRoute] = []

    if not task_spec.requires_model:
        if policy is ExecutionPolicy.REQUIRE_MODEL_OVERRIDE:
            return tuple()
        if has_default:
            routes.append(
                ExecutionRoute(
                    route_kind=RouteKind.DEFAULT_EXECUTOR,
                    task_kind=task_spec.kind,
                )
            )
        return tuple(routes)

    if model_registration is None:
        return tuple()

    has_override = model_registration.check_task_override(task_spec.kind)

    if policy is ExecutionPolicy.REQUIRE_MODEL_OVERRIDE:
        if has_override:
            routes.append(
                ExecutionRoute(
                    route_kind=RouteKind.MODEL_OVERRIDE,
                    task_kind=task_spec.kind,
                )
            )
        return tuple(routes)

    if policy is ExecutionPolicy.PREFER_MODEL_OVERRIDE and has_override:
        routes.append(
            ExecutionRoute(
                route_kind=RouteKind.MODEL_OVERRIDE,
                task_kind=task_spec.kind,
            )
        )

    if has_default:
        routes.append(
            ExecutionRoute(
                route_kind=RouteKind.DEFAULT_EXECUTOR,
                task_kind=task_spec.kind,
            )
        )

    return tuple(routes)
