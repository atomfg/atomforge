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
    energy: float
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

    def __init__(self, structure: Structure, properties: frozenset[Property]):
        super().__init__()
        self.structure = structure
        self.properties = properties

    @property
    def task_name(self) -> str:
        return KIND

    @property
    def required_properties(self) -> frozenset[str]:
        return frozenset({"energy", "forces"})
    
    def to_spec(self) -> SinglePointSpec:
        return SinglePointSpec(
            structure=self.structure.to_message(),
            properties=self.properties
        )