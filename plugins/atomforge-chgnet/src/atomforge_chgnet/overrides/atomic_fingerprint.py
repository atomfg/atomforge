from atomforge_core.task.executor import (
    TaskExecutionContext,
    TaskExecutor,
    require_model_executor,
)
from atomforge_builtins.task.atomic_descriptor.spec import AtomicDescriptor
from atomforge_builtins.task.atomic_descriptor.result import AtomicDescriptorResult
from atomforge_chgnet.executor import CHGNetExecutor


class AtomicFingerprintExecutor(TaskExecutor[AtomicDescriptor, AtomicDescriptorResult]):
    def execute(
        self, spec: AtomicDescriptor, context: TaskExecutionContext
    ) -> AtomicDescriptorResult:
        model_executor = require_model_executor(context, task_kind=spec.kind)
        atomic_fingerprints = model_executor.compute_atomic_descriptors(spec.structure)
        return AtomicDescriptorResult(descriptor=atomic_fingerprints, natoms=len(spec.structure.numbers))
