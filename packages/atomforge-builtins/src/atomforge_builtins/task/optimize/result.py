from typing import Literal

from atomforge_core.structure import StructureData
from atomforge_core.task.result import TaskResult

from atomforge_builtins.task.optimize.definitions import KIND


class OptimizeResult(TaskResult):
    kind: Literal["optimize"] = KIND
    structure: StructureData
    energy: float
    forces: list[list[float]]
    converged: bool
    steps: int
