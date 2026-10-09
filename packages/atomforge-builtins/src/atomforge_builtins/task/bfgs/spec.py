from typing import Literal

from pydantic import Field

from atomforge_core.structure import StructureData
from atomforge_core.task.spec import TaskSpec

from atomforge_builtins.task.bfgs.definitions import KIND


class BFGS(TaskSpec):
    kind: Literal["bfgs"] = KIND
    structure: StructureData
    fmax: float = 0.05
    max_steps: int = Field(default=1000, gt=0)

    def required_model_properties(self) -> frozenset:
        from atomforge_core.property import Property

        return frozenset({Property.ENERGY, Property.FORCES})
