from atomforge.model.base.executor import ModelExecutor
from atomforge.model.base.property import Property

from typing import Literal

from pydantic import Field, field_validator

from .base.executor import TaskExecutor
from .base.result import TaskResult
from .base.spec import TaskSpec
from atomforge.structure import StructureLike

KIND = "single_point"


class SinglePoint(TaskSpec):
    kind: Literal["single_point"] = KIND
    structure: StructureLike
    properties: frozenset[Property] = Field(
        default_factory=lambda: frozenset({Property.ENERGY, Property.FORCES})
    )

    def required_model_properties(self) -> frozenset[Property]:
        return self.properties

    @staticmethod
    def _normalize_properties(
        properties: list[Property] | list[str] | frozenset[Property] | None,
    ) -> frozenset[Property]:
        if properties is None:
            return frozenset({Property.ENERGY, Property.FORCES})
        elif len(properties) == 0:
            raise ValueError("At least one property must be requested.")

        if any(isinstance(p, str) for p in properties):
            properties = [
                Property(p.lower()) if isinstance(p, str) else p for p in properties
            ]

        properties = frozenset(properties)
        allowed = frozenset({Property.ENERGY, Property.FORCES})
        if not properties.issubset(allowed):
            raise ValueError(
                f"Invalid properties: {properties - allowed}. Valid properties are: {allowed}"
            )

        return properties

    @field_validator("properties", mode="before")
    @classmethod
    def validate_properties(cls, value):
        return cls._normalize_properties(value)


class SinglePointResult(TaskResult):
    kind: Literal["single_point"] = KIND
    energy: float | None
    forces: list[list[float]] | None


class SinglePointExecutor(TaskExecutor[SinglePoint, SinglePointResult]):
    def execute(
        self, spec: SinglePoint, model_executor: ModelExecutor
    ) -> SinglePointResult:
        structure = spec.get_structure()
        properties = spec.properties
        model_result = model_executor.compute(structure, properties)
        return SinglePointResult(
            energy=model_result.energy,
            forces=model_result.forces.tolist()
            if model_result.forces is not None
            else None,
        )
