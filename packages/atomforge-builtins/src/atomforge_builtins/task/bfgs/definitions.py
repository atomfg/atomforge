from atomforge_core.property import Property
from atomforge_core.task.capability import TaskCapabilitySpec

KIND = "bfgs"

BFGSCapabilitySpec = TaskCapabilitySpec(
    required=frozenset({Property.ENERGY, Property.FORCES}),
    optional=frozenset(),
)
