from atomforge_core.property import Property
from atomforge_core.task.capability import TaskCapabilitySpec

KIND = "single_point"

SinglePointCapabilitySpec = TaskCapabilitySpec(
    required=frozenset(),
    optional=frozenset(
        {
            Property.ENERGY,
            Property.FORCES,
            Property.STRESS,
            Property.MAGMOMS,
            Property.ENERGIES,
        }
    ),
)
