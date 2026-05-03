from atomforge_core.task.executability import CompatibilityCheck
from atomforge_core.task.executor import (
    TaskExecutionContext,
    TaskExecutor,
    require_model_executor,
)

from atomforge_builtins.task.single_point.result import SinglePointResult
from atomforge_builtins.task.single_point.spec import SinglePoint


class SinglePointExecutor(TaskExecutor[SinglePoint, SinglePointResult]):
    @classmethod
    def check_compatibility(
        cls, spec: SinglePoint, context: TaskExecutionContext
    ) -> CompatibilityCheck:
        return CompatibilityCheck(ok=True)

    def execute(
        self, spec: SinglePoint, context: TaskExecutionContext
    ) -> SinglePointResult:
        model_executor = require_model_executor(context, task_kind=spec.kind)
        structure = spec.structure
        properties = spec.properties
        model_result = model_executor.compute(structure, properties)
        return SinglePointResult(
            energy=model_result.energy,
            forces=model_result.forces if model_result.forces is not None else None,
            stress=model_result.stress if model_result.stress is not None else None,
            magmoms=model_result.magmoms if model_result.magmoms is not None else None,
            energies=model_result.energies
            if model_result.energies is not None
            else None,
        )
