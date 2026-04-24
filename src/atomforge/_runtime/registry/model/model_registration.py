from dataclasses import dataclass, field
from typing import Generic

from atomforge._core.env.factory import EnvironmentFactory
from atomforge._core.model.executor import ModelExecutor
from atomforge._core.model.metadata import ModelMetadata
from atomforge._core.property import Property
from atomforge._core.resources.resource_caps import ResourceCapabilities
from atomforge._core.model.spec import ModelSpecT
from atomforge._core.resources.resource_probes import ResourceProbe


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
