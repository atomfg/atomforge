from typing import Literal

from pydantic import Field

from atomforge_core.property import Property
from atomforge_core.structure import StructureData
from atomforge_core.task.spec import TaskSpec

from atomforge_builtins.task.analyze_symmetry.definitions import KIND


class AnalyzeSymmetry(TaskSpec):
    requires_model = False
    kind: Literal["analyze_symmetry"] = KIND
    structure: StructureData = Field(
        description="Input structure to analyze for crystallographic symmetry."
    )
    symprec: float = Field(
        default=0.01,
        description="Distance tolerance used by pymatgen when determining symmetry equivalence.",
    )
    angle_tolerance: float = Field(
        default=5.0,
        description="Angular tolerance in degrees used during symmetry analysis.",
    )
    return_primitive: bool = Field(
        default=False,
        description="Whether to include the standardized primitive structure in the result.",
    )
    return_conventional: bool = Field(
        default=False,
        description="Whether to include the standardized conventional structure in the result.",
    )

    def required_model_properties(self) -> frozenset[Property]:
        return frozenset()
