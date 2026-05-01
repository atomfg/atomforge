from atomforge_core.model.executor import ModelExecutor
from atomforge_core.task.executability import CompatibilityCheck
from atomforge_core.task.executor import TaskExecutor

from atomforge_builtins.task.single_point.result import SinglePointResult
from atomforge_builtins.task.single_point.spec import SinglePoint


class SinglePointExecutor(TaskExecutor[SinglePoint, SinglePointResult]):
    @classmethod
    def check_compatibility(
        cls, spec: SinglePoint, model_executor: ModelExecutor
    ) -> CompatibilityCheck:
        return CompatibilityCheck(ok=True)

    def execute(
        self, spec: SinglePoint, model_executor: ModelExecutor
    ) -> SinglePointResult:
        structure = spec.structure
        properties = spec.properties
        model_result = model_executor.compute(structure, properties)
        return SinglePointResult(
            energy=model_result.energy,
            forces=model_result.forces
            if model_result.forces is not None
            else None,
        )
