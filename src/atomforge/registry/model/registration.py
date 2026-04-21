from dataclasses import dataclass, field
from typing import Generic

from atomforge.env.base.factory import EnvironmentFactory
from atomforge.model.core.executor import ModelExecutor
from atomforge.model.core.metadata import ModelMetadata
from atomforge.model.core.property import Property
from atomforge.model.core.resource_caps import ResourceCapabilities
from atomforge.model.core.spec import ModelSpecT
from atomforge.model.probes import ResourceProbe


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
