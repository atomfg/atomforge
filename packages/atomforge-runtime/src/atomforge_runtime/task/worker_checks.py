from __future__ import annotations

from atomforge_core.task.executability import CompatibilityCheck
from atomforge_core.task.executor import TaskExecutionContext, TaskExecutor
from atomforge_core.task.spec import TaskSpec


def check_executor_compatibility(
    task_spec: TaskSpec,
    task_executor_cls: type[TaskExecutor],
    context: TaskExecutionContext,
) -> CompatibilityCheck:
    if task_spec.requires_model and context.model_executor is None:
        return CompatibilityCheck(
            ok=False,
            reason=(
                f"Task of kind {task_spec.kind} requires a model executor, "
                "but none was provided"
            ),
        )
    return task_executor_cls.check_compatibility(task_spec, context)
