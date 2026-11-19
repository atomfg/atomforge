from typing import Any, Literal

from atomforge_core.task.result import TaskResult

from atomforge_builtins.task.describe_model_result.definitions import KIND


class DescribeModelResultResult(TaskResult):
    kind: Literal["describe_model_result"] = KIND
    # Field name (energy, forces, ...) to its description; see
    # ``executor.describe_field``.
    fields: dict[str, dict[str, Any]]
