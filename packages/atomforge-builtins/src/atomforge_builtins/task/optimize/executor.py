from typing import TYPE_CHECKING

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
from atomforge_builtins.task.optimize.result import OptimizeResult
from atomforge_builtins.task.optimize.spec import (
    FixAtomsConstraint,
    FixCartesianConstraint,
    Optimize,
    OptimizeConstraint,
)

if TYPE_CHECKING:
    from ase.optimize.optimize import Optimizer

OptimizerName = str


def optimizer_class_for(name: OptimizerName) -> type["Optimizer"]:
    from ase.optimize import BFGS, FIRE, LBFGS

    optimizer_map: dict[OptimizerName, type["Optimizer"]] = {
        "bfgs": BFGS,
        "lbfgs": LBFGS,
        "fire": FIRE,
    }
    return optimizer_map[name]


def constraint_to_ase(constraint: OptimizeConstraint):
    from ase.constraints import FixAtoms, FixCartesian

    if isinstance(constraint, FixAtomsConstraint):
        return FixAtoms(indices=list(constraint.indices))
    if isinstance(constraint, FixCartesianConstraint):
        return FixCartesian(
            list(constraint.indices),
            mask=tuple(constraint.mask),
        )
    raise TypeError(f"Unsupported constraint type: {type(constraint)!r}")


class OptimizeExecutor(TaskExecutor[Optimize, OptimizeResult]):
    @classmethod
    def check_compatibility(
        cls, spec: Optimize, context: TaskExecutionContext
    ) -> CompatibilityCheck:
        return CompatibilityCheck(ok=True)

    def execute(self, spec: Optimize, context: TaskExecutionContext) -> OptimizeResult:
        optimizer_cls = optimizer_class_for(spec.optimizer)

        model_executor = require_model_executor(context, task_kind=spec.kind)
        atoms = convert_to_atoms(spec.structure)
        atoms.calc = ModelCalculatorAdapter(model_executor)
        if spec.constraints:
            atoms.set_constraint([constraint_to_ase(c) for c in spec.constraints])

        optimizer = optimizer_cls(atoms)
        if spec.max_steps is None:
            converged = optimizer.run(fmax=spec.fmax)
        else:
            converged = optimizer.run(fmax=spec.fmax, steps=spec.max_steps)

        final_structure = convert_to_structure(atoms)
        energy = atoms.get_potential_energy()
        forces = atoms.get_forces()
        return OptimizeResult(
            structure=final_structure,
            energy=energy,
            forces=forces.tolist(),
            converged=bool(converged),
            steps=optimizer.nsteps,
        )
