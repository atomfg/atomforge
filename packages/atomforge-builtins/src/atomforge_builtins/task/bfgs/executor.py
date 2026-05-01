from atomforge_core.model.executor import ModelExecutor
from atomforge_core.task.executability import CompatibilityCheck
from atomforge_core.task.executor import TaskExecutor

from atomforge_builtins.task.bfgs.adapters import (
    ModelCalculatorAdapter,
    convert_to_atoms,
    convert_to_structure,
)
from atomforge_builtins.task.bfgs.result import BFGSResult
from atomforge_builtins.task.bfgs.spec import BFGS


class BFGSExecutor(TaskExecutor[BFGS, BFGSResult]):
    @classmethod
    def check_compatibility(
        cls, spec: BFGS, model_executor: ModelExecutor
    ) -> CompatibilityCheck:
        return CompatibilityCheck(ok=True)

    def execute(self, spec: BFGS, model_executor: ModelExecutor) -> BFGSResult:
        from ase.optimize import BFGS as BFGSOptimizer

        atoms = convert_to_atoms(spec.structure)
        atoms.calc = ModelCalculatorAdapter(model_executor)
        optimizer = BFGSOptimizer(atoms)
        optimizer.run(fmax=spec.fmax)

        final_structure = convert_to_structure(atoms)
        energy = atoms.get_potential_energy()
        forces = atoms.get_forces()
        return BFGSResult(
            structure=final_structure,
            energy=energy,
            forces=forces.tolist(),
        )
