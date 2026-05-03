from atomforge_core.property import Property
from atomforge_core.task.executability import CompatibilityCheck
from atomforge_core.task.executor import (
    TaskExecutionContext,
    TaskExecutor,
    require_model_executor,
)

from atomforge_builtins.task.batch_single_point.result import BatchSinglePointResult
from atomforge_builtins.task.batch_single_point.spec import BatchSinglePoint


class BatchSinglePointExecutor(
    TaskExecutor[BatchSinglePoint, BatchSinglePointResult]
):
    @classmethod
    def check_compatibility(
        cls, spec: BatchSinglePoint, context: TaskExecutionContext
    ) -> CompatibilityCheck:
        return CompatibilityCheck(ok=True)

    def execute(
        self, spec: BatchSinglePoint, context: TaskExecutionContext
    ) -> BatchSinglePointResult:
        model_executor = require_model_executor(context, task_kind=spec.kind)
        structures = spec.structures
        properties = spec.properties
        results = []
        for structure in structures:
            model_result = model_executor.compute(structure, properties)
            results.append(model_result)

        if Property.ENERGY in properties:
            energies = [result.energy for result in results]
        else:
            energies = None

        if Property.FORCES in properties:
            forces = [result.forces for result in results]
        else:
            forces = None

        return BatchSinglePointResult(
            energy=energies,
            forces=forces,
        )
