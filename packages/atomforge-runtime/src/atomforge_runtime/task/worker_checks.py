from __future__ import annotations

from atomforge_core.model.executor import ModelExecutor
from atomforge_core.task.executability import CompatibilityCheck
from atomforge_core.task.executor import TaskExecutor
from atomforge_core.task.spec import TaskSpec


def check_executor_compatibility(
    task_spec: TaskSpec,
    task_executor_cls: type[TaskExecutor],
    model_executor: ModelExecutor,
) -> CompatibilityCheck:
    return task_executor_cls.check_compatibility(task_spec, model_executor)
