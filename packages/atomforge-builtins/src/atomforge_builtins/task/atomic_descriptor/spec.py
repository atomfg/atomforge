from atomforge_core.property import Property
from atomforge_core.structure import StructureData
from atomforge_core.task.spec import TaskSpec

from atomforge_builtins.task.atomic_descriptor.definitions import KIND
from atomforge_core.task.execution_policy import ExecutionPolicy
from typing import Literal
    
class AtomicDescriptor(TaskSpec):
    execution_policy: Literal[ExecutionPolicy.REQUIRE_MODEL_OVERRIDE] = ExecutionPolicy.REQUIRE_MODEL_OVERRIDE
    kind: str = KIND
    structure: StructureData

    def required_model_properties(self) -> frozenset[Property]:
        return frozenset()
