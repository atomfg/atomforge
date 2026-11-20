from typing import Any, Literal

from atomforge_core.task.result import TaskResult

from atomforge_builtins.task.describe_model_result.definitions import KIND


class DescribeModelResultResult(TaskResult):
    kind: Literal["describe_model_result"] = KIND
    # Field name (energy, forces, ...) to its description; see
    # ``executor.describe_field``.
    fields: dict[str, dict[str, Any]]
    # Fields of the first result that the compute on the later structure
    # changed; None when no later structure was given.
    changed_by_later_compute: list[str] | None = None
