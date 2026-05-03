from typing import Literal

from atomforge_core.structure import StructureData
from atomforge_core.task.result import TaskResult

from atomforge_builtins.task.analyze_symmetry.definitions import KIND


class AnalyzeSymmetryResult(TaskResult):
    kind: Literal["analyze_symmetry"] = KIND
    space_group_symbol: str
    space_group_number: int
    crystal_system: str
    lattice_type: str
    point_group_symbol: str
    primitive_structure: StructureData | None = None
    conventional_structure: StructureData | None = None
