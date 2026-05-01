from typing import Literal

from pydantic import Field, field_validator

from atomforge_core.env.env import EnvironmentSpec
from atomforge_core.model.executor import ModelExecutor
from atomforge_core.property import Property
from atomforge_core.structure import StructureData
from atomforge_core.task.capability import TaskCapabilitySpec
from atomforge_core.task.executability import CompatibilityCheck
from atomforge_core.task.executor import TaskExecutor
from atomforge_core.task.result import TaskResult
from atomforge_core.task.spec import TaskSpec
from atomforge_core.env.factory import (
    DependencySummary,
    environment_factory_from_callable,
)

KIND = "batch_single_point"

BatchSinglePointCapabilitySpec = TaskCapabilitySpec(
    required=frozenset(),
    optional=frozenset({Property.ENERGY, Property.FORCES}),
)


class BatchSinglePoint(TaskSpec):
    kind: Literal["batch_single_point"] = KIND
    structures: tuple[StructureData, ...]
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


BatchSinglePointEnvironmentFactory = environment_factory_from_callable(
    lambda spec: EnvironmentSpec(name="batch_single_point"),
    DependencySummary(base_requirements=[]),
)


class BatchSinglePointResult(TaskResult):
    kind: Literal["batch_single_point"] = KIND
    energy: list[float ] | None
    forces: list[list[list[float]]] | None


class BatchSinglePointExecutor(TaskExecutor[BatchSinglePoint, BatchSinglePointResult]):
    @classmethod
    def check_compatibility(
        cls, spec: BatchSinglePoint, model_executor: ModelExecutor
    ) -> CompatibilityCheck:
        return CompatibilityCheck(ok=True)

    def execute(
        self, spec: BatchSinglePoint, model_executor: ModelExecutor
    ) -> BatchSinglePointResult:
        structures = spec.structures
        properties = spec.properties
        results = []
        for structure in structures:
            model_result = model_executor.compute(structure, properties)
            results.append(model_result)
        
        if Property.ENERGY in properties:
            energies = [result.energy for result in results]
        else:
            energies = None

        if Property.FORCES in properties:
            forces = [result.forces for result in results]            
        else:
            forces = None

        return BatchSinglePointResult(
            energy=energies,
            forces=forces
        )
