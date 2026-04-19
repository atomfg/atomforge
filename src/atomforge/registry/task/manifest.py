from dataclasses import dataclass

@dataclass
class TaskManifest:
    kind: str
    spec_model: str
    executor_class: str
    result_model: str
    capability_spec: str
    environment_factory: str

