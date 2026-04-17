from atomforge.env.base.env import EnvironmentSpec
from atomforge.model.base.executor import ModelExecutor
from atomforge.model.base.property import Property
from atomforge.structure import Structure, StructureMessage

from typing import Literal

from .base.base import Task, TaskCapabilitySpec
from .base.executor import TaskExecutor
from .base.result import TaskResult
from .base.spec import TaskSpec

KIND = "single_point"


class SinglePointSpec(TaskSpec):
    kind: Literal["single_point"] = KIND
    structure: StructureMessage
    properties: frozenset[Property]


class SinglePointResult(TaskResult):
    kind: Literal["single_point"] = KIND
    energy: float | None
    forces: list[list[float]] | None


class SinglePointExecutor(TaskExecutor):
    def execute(
        self, spec: SinglePointSpec, model_executor: ModelExecutor
    ) -> SinglePointResult:
        structure = spec.structure.to_structure()
        properties = spec.properties
        model_result = model_executor.compute(structure, properties)
        return SinglePointResult(
            energy=model_result.energy,
            forces=model_result.forces.tolist()
            if model_result.forces is not None
            else None,
        )


class SinglePoint(Task):
    capability_spec = TaskCapabilitySpec(
        required=frozenset(), optional=frozenset({Property.ENERGY, Property.FORCES})
    )
    task_name = KIND

    def __init__(
        self, structure: Structure, properties: list[Property] | list[str] | None = None
    ) -> None:
        super().__init__()
        self.structure = structure

        if properties is None:  # Not given, default to energy and forces
            properties = [Property.ENERGY, Property.FORCES]
        elif len(properties) == 0:  # Given but empty, not valid.
            raise ValueError("At least one property must be requested.")

        # Convert list of strings to frozenset of Properties.
        if all(isinstance(p, str) for p in properties):
            properties = frozenset([Property(p) for p in properties])

        # Convert list of Properties to frozenset of Properties.
        elif all(isinstance(p, Property) for p in properties):
            properties = frozenset(properties)

        # Mixed types are not valid.
        elif not all(isinstance(p, Property) for p in properties):
            raise ValueError(
                "Properties must be either all strings or all Property instances."
            )

        # Check that all requested properties are in the declared capability spec for this task
        if not properties.issubset(
            self.capability_spec.optional.union(self.capability_spec.required)
        ):
            raise ValueError(
                f"Invalid properties: {properties - self.capability_spec.optional.union(self.capability_spec.required)}. Valid properties are: {self.capability_spec.optional.union(self.capability_spec.required)}"
            )
        self.requested_properties: frozenset[Property] = properties

    def _required_model_properties(self):
        return self.requested_properties

    def to_spec(self) -> SinglePointSpec:
        return SinglePointSpec(
            structure=self.structure.to_message(), properties=self.requested_properties
        )

    def executor_environment(self) -> EnvironmentSpec:
        return EnvironmentSpec(name=self.task_name)
