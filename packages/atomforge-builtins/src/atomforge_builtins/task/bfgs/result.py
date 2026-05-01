from typing import Literal

from atomforge_core.structure import StructureData
from atomforge_core.task.result import TaskResult

from atomforge_builtins.task.bfgs.definitions import KIND


class BFGSResult(TaskResult):
    kind: Literal["bfgs"] = KIND
    structure: StructureData
    energy: float
    forces: list[list[float]]
