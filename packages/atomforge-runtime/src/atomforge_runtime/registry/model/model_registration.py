from dataclasses import dataclass, field
from typing import Generic

from atomforge_core.env.factory import EnvironmentFactory
from atomforge_core.model.executor import ModelExecutor
from atomforge_core.model.metadata import ModelMetadata
from atomforge_core.property import Property
from atomforge_core.resources.resource_caps import ResourceCapabilities
from atomforge_core.model.spec import ModelSpecT
from atomforge_core.resources.resource_probes import ResourceProbe


@dataclass(frozen=True)
class ModelRegistration(Generic[ModelSpecT]):
    model_spec: type[ModelSpecT]
    metadata: ModelMetadata
    executor_class: type[ModelExecutor[ModelSpecT]]
    supported_properties: frozenset[Property]
    environment_factory: EnvironmentFactory[ModelSpecT]
    resource_capabilities: ResourceCapabilities
    probe: ResourceProbe | None = None
    source: list[str] = field(default_factory=list)
