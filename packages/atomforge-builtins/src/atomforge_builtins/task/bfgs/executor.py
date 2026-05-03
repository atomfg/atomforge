from atomforge_core.task.executability import CompatibilityCheck
from atomforge_core.task.executor import (
    TaskExecutionContext,
    TaskExecutor,
    require_model_executor,
)

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
        cls, spec: BFGS, context: TaskExecutionContext
    ) -> CompatibilityCheck:
        return CompatibilityCheck(ok=True)

    def execute(self, spec: BFGS, context: TaskExecutionContext) -> BFGSResult:
        from ase.optimize import BFGS as BFGSOptimizer

        model_executor = require_model_executor(context, task_kind=spec.kind)
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
