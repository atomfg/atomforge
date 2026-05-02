from atomforge_core.property import Property
from atomforge_core.task.capability import TaskCapabilitySpec

KIND = "optimize"

OptimizeCapabilitySpec = TaskCapabilitySpec(
    required=frozenset({Property.ENERGY, Property.FORCES}),
    optional=frozenset(),
)
