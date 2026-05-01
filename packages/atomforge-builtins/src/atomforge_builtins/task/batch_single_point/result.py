from typing import Literal

from atomforge_core.task.result import TaskResult

from atomforge_builtins.task.batch_single_point.definitions import KIND


class BatchSinglePointResult(TaskResult):
    kind: Literal["batch_single_point"] = KIND
    energy: list[float] | None
    forces: list[list[list[float]]] | None
