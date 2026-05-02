from typing import Literal

from atomforge_core.task.result import TaskResult

from atomforge_builtins.task.single_point.definitions import KIND


class SinglePointResult(TaskResult):
    kind: Literal["single_point"] = KIND
    energy: float | None
    forces: list[list[float]] | None
    stress: list[list[float]] | None
    magmoms: list[float] | None
    energies: list[float] | None
