from atomforge_core.property import Property
from atomforge_core.task.capability import TaskCapabilitySpec

KIND = "describe_model_result"

DescribeModelResultCapabilitySpec = TaskCapabilitySpec(
    required=frozenset(),
    optional=frozenset(Property),
)
