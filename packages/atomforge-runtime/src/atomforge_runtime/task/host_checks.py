from __future__ import annotations

from atomforge_core.task.executability import HostExecutabilityReport
from atomforge_core.task.spec import TaskSpec
from atomforge_runtime.registry.model.model_registration import ModelRegistration
from atomforge_runtime.registry.task.task_registration import TaskRegistration
from atomforge_runtime.task.routing import resolve_candidate_routes


def check_required_properties(
    task_spec: TaskSpec,
    model_registration: ModelRegistration,
) -> HostExecutabilityReport:
    model_supported_properties = model_registration.load_supported_properties()
    task_required_properties = task_spec.required_model_properties()
    if not task_required_properties.issubset(model_supported_properties):
        return HostExecutabilityReport.failure(
            reason=(
                f"Model of kind {model_registration.kind} does not support task of "
                f"kind {task_spec.kind}: required properties {task_required_properties} "
                f"are not a subset of supported properties {model_supported_properties}"
            )
        )
    return HostExecutabilityReport.success()


def check_host_executability(
    task_spec: TaskSpec,
    task_registration: TaskRegistration,
    model_registration: ModelRegistration,
) -> HostExecutabilityReport:
    property_report = check_required_properties(task_spec, model_registration)
    if not property_report.ok:
        return property_report

    candidate_routes = resolve_candidate_routes(
        task_spec,
        task_registration,
        model_registration,
    )
    if not candidate_routes:
        return HostExecutabilityReport.failure(
            reason=(
                f"No policy-allowed executor route found for task kind "
                f"'{task_spec.kind}' and model kind '{model_registration.kind}'"
            )
        )

    return HostExecutabilityReport.success_with_routes(candidate_routes=candidate_routes)
