from typing import Literal

from atomforge_core.env.env import EnvironmentSpec
from atomforge_core.model.executor import ModelExecutor
from atomforge_core.property import Property
from atomforge_core.structure import StructureData
from atomforge_core.task.capability import TaskCapabilitySpec
from atomforge_core.task.executor import TaskExecutor
from atomforge_core.task.result import TaskResult
from atomforge_core.task.spec import TaskSpec
from atomforge_core.env.factory import (
    DependencySummary,
    environment_factory_from_callable,
)

KIND = "bfgs"

BFGSCapabilitySpec = TaskCapabilitySpec(
    required=frozenset({Property.ENERGY, Property.FORCES}),
    optional=frozenset(),
)


class BFGS(TaskSpec):
    kind: Literal["bfgs"] = KIND
    structure: StructureData
    fmax: float = 0.05

    def required_model_properties(self) -> frozenset[Property]:
        return frozenset({Property.ENERGY, Property.FORCES})


class BFGSResult(TaskResult):
    kind: Literal["bfgs"] = KIND
    structure: StructureData
    energy: float
    forces: list[list[float]]


BFGSEnvironmentFactory = environment_factory_from_callable(
    lambda spec: EnvironmentSpec(name="bfgs", requirements=["ase"]),
    DependencySummary(base_requirements=["ase"]),
)


class BFGSExecutor(TaskExecutor[BFGS, BFGSResult]):
    def execute(self, spec: BFGS, model_executor: ModelExecutor) -> BFGSResult:
        from ase.calculators.calculator import Calculator
        from ase.optimize import BFGS as BFGSOptimizer

        class ModelCalculatorAdapter(Calculator):
            implemented_properties = ["energy", "forces"]

            def __init__(self, model_executor: ModelExecutor):
                super().__init__()
                self.model_executor = model_executor
        

            def calculate(self, atoms, properties=None, system_changes=None):
                structure = convert_to_structure(atoms)
                model_result = self.model_executor.compute(
                    structure, {Property.ENERGY, Property.FORCES}
                )
                self.results["energy"] = model_result.energy
                self.results["forces"] = model_result.forces

        # Setup
        atoms = convert_to_atoms(spec.structure)
        atoms.calc = ModelCalculatorAdapter(model_executor)
        optimizer = BFGSOptimizer(atoms)

        # Run optimization
        optimizer.run(fmax=spec.fmax)

        # Collect results
        final_structure = convert_to_structure(atoms)
        energy = atoms.get_potential_energy()
        forces = atoms.get_forces()
        return BFGSResult(
            structure=final_structure,
            energy=energy,
            forces=forces.tolist(),
        )
    

def convert_to_atoms(structure: StructureData):
    from ase import Atoms
    return Atoms(
        numbers=structure.numbers,
        positions=structure.positions,
        cell=structure.cell,
        pbc=structure.pbc,
    )

def convert_to_structure(atoms) -> StructureData:
    return StructureData(
        numbers=atoms.get_atomic_numbers().tolist(),
        positions=atoms.get_positions().tolist(),
        cell=atoms.get_cell().tolist(),
        pbc=atoms.get_pbc().tolist(),
    )

