from .base import Task, TaskExecutor, TaskSpec, TaskResult
from atomforge.model.base import Property, Model
from atomforge.structure import Structure, StructureMessage

from typing import Literal

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
    
    def execute(self, spec: SinglePointSpec, model: Model) -> SinglePointResult:
        structure = spec.structure.to_structure()
        properties = spec.properties
        model_result = model.compute(structure, properties)
        return SinglePointResult(
            energy=model_result.energy,
            forces=model_result.forces.tolist() if model_result.forces is not None else None,
        )

class SinglePoint(Task):

    def __init__(self, structure: Structure, properties: list[Property] | list[str]):
        super().__init__()
        self.structure = structure

        if all(isinstance(p, str) for p in properties):
            properties = [Property(p) for p in properties]
        elif not all(isinstance(p, Property) for p in properties):
            raise ValueError("Properties must be either all strings or all Property instances.")

        self.properties = properties

    @property
    def task_name(self) -> str:
        return KIND

    @property
    def required_properties(self) -> frozenset[str]:
        """
        This is eventually meant to specify what a model needs to expose to be able to execute this task.

        It is however, currently ignored.
        """
        return frozenset({Property.ENERGY, Property.FORCES})
    
    def to_spec(self) -> SinglePointSpec:
        return SinglePointSpec(
            structure=self.structure.to_message(),
            properties=self.properties
        )