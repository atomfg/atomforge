from .base import Task, TaskExecutor, TaskSpec, TaskResult, TaskCapabilitySpec
from atomforge.model.base import Property, Model
from atomforge.structure import Structure, StructureMessage

from typing import Literal

KIND = "bfgs"


class BFGSSpec(TaskSpec):
    kind: Literal["bfgs"] = KIND
    structure: StructureMessage
    fmax: float = 0.05

class BFGSResult(TaskResult):
    kind: Literal["bfgs"] = KIND
    structure: StructureMessage
    energy: float
    forces: list[list[float]]


class BFGSExecutor(TaskExecutor):

    def execute(self, spec: BFGSSpec, model: Model) -> BFGSResult:
        from ase.optimize import BFGS as BFGSOptimizer
        from ase.calculators.calculator import Calculator

        class ModelCalculatorAdapter(Calculator):

            implemented_properties = ["energy", "forces"]

            def __init__(self, model: Model):
                super().__init__()
                self.model = model

            def calculate(self, atoms, properties=None, system_changes=None):
                structure = Structure.from_ase(atoms)
                model_result = self.model.compute(structure, {Property.ENERGY, Property.FORCES})
                self.results["energy"] = model_result.energy
                self.results["forces"] = model_result.forces
    
        # Setup
        atoms = spec.structure.to_structure().to_ase()
        atoms.set_calculator(ModelCalculatorAdapter(model))
        optimizer = BFGSOptimizer(atoms)

        # Run optimization
        optimizer.run(fmax=spec.fmax)

        # Collect results
        final_structure = Structure.from_ase(atoms)
        energy = atoms.get_potential_energy()
        forces = atoms.get_forces()
        return BFGSResult(
            structure=final_structure.to_message(),
            energy=energy,
            forces=forces.tolist())

class BFGS(Task):
    capability_spec = TaskCapabilitySpec(
        required=frozenset({Property.ENERGY, Property.FORCES}), optional=frozenset()
    )
    task_name = KIND

    def __init__(
        self, structure: Structure, fmax: float = 0.05) -> None:
        super().__init__()
        self.structure = structure
        self.fmax = fmax

    def _required_model_properties(self):
        return self.capability_spec.required

    def to_spec(self) -> BFGSSpec:
        return BFGSSpec(
            structure=self.structure.to_message(),
            fmax=self.fmax
        )
