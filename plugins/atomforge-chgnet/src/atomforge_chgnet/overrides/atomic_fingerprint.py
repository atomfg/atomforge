from atomforge_core.task.executor import TaskExecutor
from atomforge_builtins.task.atomic_descriptor.spec import AtomicDescriptor
from atomforge_builtins.task.atomic_descriptor.result import AtomicDescriptorResult
from atomforge_chgnet.executor import CHGNetExecutor


class AtomicFingerprintExecutor(TaskExecutor[AtomicDescriptor, AtomicDescriptorResult]):
    def execute(
        self, spec: AtomicDescriptor, model_executor: CHGNetExecutor
    ) -> AtomicDescriptorResult:
        atomic_fingerprints = model_executor.compute_atomic_descriptors(spec.structure)
        return AtomicDescriptorResult(descriptor=atomic_fingerprints, natoms=len(spec.structure.numbers))
