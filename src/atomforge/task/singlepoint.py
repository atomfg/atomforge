from .base import Task
from atomforge.model.base import Property, ModelResult, Model
from atomforge.structure import Structure

class SinglePoint(Task):

    @property
    def task_name(self) -> str:
        return "single_point"

    @property
    def required_properties(self) -> frozenset[str]:
        return frozenset({"energy", "forces"})

    def run(self, structure: Structure, model: Model):
        model_result = model.compute(structure, self.required_properties)
        return model_result