from __future__ import annotations

from atomforge_core.task.executability import (
    CompatibilityCheck,
    ExecutionRoute,
    HostExecutabilityReport,
    RouteKind,
)
from atomforge_core.task.executor import TaskExecutionContext, TaskExecutor
from atomforge_core.task.spec import TaskSpec
from atomforge_runtime.registry.model.model_registration import ModelRegistration
from atomforge_runtime.registry.task.task_registration import TaskRegistration
from atomforge_runtime.task.host_checks import check_host_executability
from atomforge_runtime.task.worker_checks import check_executor_compatibility


def resolve_host_execution(
    task_spec: TaskSpec,
    task_registration: TaskRegistration,
    model_registration: ModelRegistration | None,
) -> HostExecutabilityReport:
    return check_host_executability(task_spec, task_registration, model_registration)


def load_executor_class_for_route(
    route: ExecutionRoute,
    task_registration: TaskRegistration,
    model_registration: ModelRegistration | None,
) -> type[TaskExecutor]:
    if route.route_kind is RouteKind.MODEL_OVERRIDE:
        if model_registration is None:
            raise ValueError(
                f"Unable to load model override executor for task kind '{route.task_kind}' "
                "without a model registration"
            )
        executor_cls = model_registration.load_task_override_executor_class(route.task_kind)
    else:
        executor_cls = task_registration.load_executor_class()

    if executor_cls is None:
        raise ValueError(
            f"Unable to load executor class for route '{route.route_kind.value}' "
            f"and task kind '{route.task_kind}'"
        )
    return executor_cls


def resolve_worker_execution(
    task_spec: TaskSpec,
    task_registration: TaskRegistration,
    model_registration: ModelRegistration | None,
    context: TaskExecutionContext,
) -> tuple[ExecutionRoute, type[TaskExecutor], CompatibilityCheck]:
    host_report = resolve_host_execution(task_spec, task_registration, model_registration)
    if not host_report.ok:
        raise ValueError(host_report.reason or "Task is not executable")

    for route in host_report.candidate_routes:
        executor_cls = load_executor_class_for_route(
            route,
            task_registration,
            model_registration,
        )
        compatibility = check_executor_compatibility(
            task_spec,
            executor_cls,
            context,
        )
        if compatibility.ok:
            return route, executor_cls, compatibility

    first_route = host_report.candidate_routes[0]
    fallback_executor_cls = load_executor_class_for_route(
        first_route,
        task_registration,
        model_registration,
    )
    compatibility = check_executor_compatibility(
        task_spec,
        fallback_executor_cls,
        context,
    )
    return first_route, fallback_executor_cls, compatibility
