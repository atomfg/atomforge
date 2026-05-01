from atomforge_core.property import Property
from atomforge_core.task.capability import TaskCapabilitySpec

KIND = "batch_single_point"

BatchSinglePointCapabilitySpec = TaskCapabilitySpec(
    required=frozenset(),
    optional=frozenset({Property.ENERGY, Property.FORCES}),
)
