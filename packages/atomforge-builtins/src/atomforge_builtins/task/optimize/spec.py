from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, field_validator

from atomforge_core.property import Property
from atomforge_core.structure import StructureData
from atomforge_core.task.spec import TaskSpec

from atomforge_builtins.task.optimize.definitions import KIND


class _ConstraintModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_default=True)

    indices: tuple[int, ...]

    @field_validator("indices")
    @classmethod
    def validate_indices(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        if len(value) == 0:
            raise ValueError("Constraint indices must not be empty.")
        if len(set(value)) != len(value):
            raise ValueError("Constraint indices must not contain duplicates.")
        return value


class FixAtomsConstraint(_ConstraintModel):
    type: Literal["fix_atoms"] = "fix_atoms"


class FixCartesianConstraint(_ConstraintModel):
    type: Literal["fix_cartesian"] = "fix_cartesian"
    mask: tuple[bool, bool, bool]


OptimizeConstraint: TypeAlias = Annotated[
    FixAtomsConstraint | FixCartesianConstraint,
    Field(discriminator="type"),
]


class Optimize(TaskSpec):
    kind: Literal["optimize"] = KIND
    structure: StructureData
    fmax: float = 0.05
    max_steps: int | None = None
    optimizer: Literal["bfgs", "lbfgs", "fire"] = "bfgs"
    constraints: tuple[OptimizeConstraint, ...] = ()

    def required_model_properties(self) -> frozenset:
        return frozenset({Property.ENERGY, Property.FORCES})
