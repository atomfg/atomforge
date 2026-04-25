from dataclasses import dataclass

from atomforge_core.property import Property


@dataclass(slots=True)
class TaskCapabilitySpec:
    required: frozenset[Property]
    optional: frozenset[Property] = frozenset()

    def __post_init__(self):
        if self.required.intersection(self.optional):
            raise ValueError("A property cannot be both required and optional.")
