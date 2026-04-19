from typing import Literal

from atomforge.env.base.env import EnvironmentSpec
from atomforge.model.core.executor import ModelExecutor
from atomforge.model.core.property import Property
from atomforge.structure import StructureLike, StructureMessage
from atomforge.task.core.capability import TaskCapabilitySpec
from atomforge.task.core.executor import TaskExecutor
from atomforge.task.core.result import TaskResult
from atomforge.task.core.spec import TaskSpec

KIND = "bfgs"

BFGSCapabilitySpec = TaskCapabilitySpec(
    required=frozenset({Property.ENERGY, Property.FORCES}),
    optional=frozenset(),
)

class BFGS(TaskSpec):
    kind: Literal["bfgs"] = KIND
    structure: StructureLike
    fmax: float = 0.05

    def required_model_properties(self) -> frozenset[Property]:
        return frozenset({Property.ENERGY, Property.FORCES})


class BFGSResult(TaskResult):
    kind: Literal["bfgs"] = KIND
    structure: StructureMessage
    energy: float
    forces: list[list[float]]

def bfgs_environment_factory(spec: BFGS) -> EnvironmentSpec:
    return EnvironmentSpec(name="bfgs", requirements=["ase"])


class BFGSExecutor(TaskExecutor[BFGS, BFGSResult]):
    def execute(self, spec: BFGS, model_executor: ModelExecutor) -> BFGSResult:
        from ase.calculators.calculator import Calculator
        from ase.optimize import BFGS as BFGSOptimizer

        from atomforge.structure import Structure

        class ModelCalculatorAdapter(Calculator):
            implemented_properties = ["energy", "forces"]

            def __init__(self, model_executor: ModelExecutor):
                super().__init__()
                self.model_executor = model_executor

            def calculate(self, atoms, properties=None, system_changes=None):
                structure = Structure.from_ase(atoms)
                model_result = self.model_executor.compute(
                    structure, {Property.ENERGY, Property.FORCES}
                )
                self.results["energy"] = model_result.energy
                self.results["forces"] = model_result.forces

        # Setup
        atoms = spec.get_structure().to_ase()
        atoms.set_calculator(ModelCalculatorAdapter(model_executor))
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
            forces=forces.tolist(),
        )


