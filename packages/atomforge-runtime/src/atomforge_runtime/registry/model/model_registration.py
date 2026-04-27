from dataclasses import dataclass, field
from typing import Generic

from atomforge_core.env.factory import EnvironmentFactory
from atomforge_core.model.executor import ModelExecutor
from atomforge_core.model.metadata import ModelMetadata
from atomforge_core.property import Property
from atomforge_core.resources.resource_caps import ResourceCapabilities
from atomforge_core.model.spec import ModelSpecT
from atomforge_core.resources.resource_probes import ResourceProbe
from atomforge_core.registry.symbol_path import SymbolPath
from atomforge_runtime.registry.loading import (
    load_callable,
    load_environment_factory,
    load_instance,
    load_subclass,
)

_UNSET = object()  # Sentinel for unset values

@dataclass(frozen=True)
class ModelRegistration(Generic[ModelSpecT]):
    kind: str
    model_spec: type[ModelSpecT]
    metadata_path: SymbolPath
    executor_class_path: SymbolPath
    supported_properties_path: SymbolPath
    environment_factory_path: SymbolPath
    resource_capabilities_path: SymbolPath
    probe_path: SymbolPath | None = None
    source: list[str] = field(default_factory=list)

    _metadata: object = field(default=_UNSET, init=False, repr=False, compare=False)
    _executor_class: object = field(default=_UNSET, init=False, repr=False, compare=False)
    _supported_properties: object = field(
        default=_UNSET, init=False, repr=False, compare=False
    )
    _environment_factory: object = field(
        default=_UNSET, init=False, repr=False, compare=False
    )
    _resource_capabilities: object = field(
        default=_UNSET, init=False, repr=False, compare=False
    )
    _probe: object = field(default=_UNSET, init=False, repr=False, compare=False)

    def load_metadata(self) -> ModelMetadata:
        if self._metadata is _UNSET:
            object.__setattr__(
                self,
                "_metadata",
                load_instance(
                    self.metadata_path,
                    ModelMetadata,
                    registration_label="Model registration",
                    kind=self.kind,
                    field_name="metadata",
                ),
            )
        return self._metadata

    def load_executor_class(self) -> type[ModelExecutor[ModelSpecT]]:
        if self._executor_class is _UNSET:
            object.__setattr__(
                self,
                "_executor_class",
                load_subclass(
                    self.executor_class_path,
                    ModelExecutor,
                    registration_label="Model registration",
                    kind=self.kind,
                    field_name="executor_class",
                ),
            )
        return self._executor_class

    def load_supported_properties(self) -> frozenset[Property]:
        if self._supported_properties is _UNSET:
            supported_properties = load_instance(
                self.supported_properties_path,
                frozenset,
                registration_label="Model registration",
                kind=self.kind,
                field_name="supported_properties",
            )
            if not all(isinstance(prop, Property) for prop in supported_properties):
                raise TypeError(
                    f"Model registration '{self.kind}' failed to load supported_properties from "
                    f"'{self.supported_properties_path}': supported_properties must contain only Property values"
                )
            object.__setattr__(self, "_supported_properties", supported_properties)
        return self._supported_properties

    def load_environment_factory(self) -> EnvironmentFactory[ModelSpecT]:
        if self._environment_factory is _UNSET:
            object.__setattr__(
                self,
                "_environment_factory",
                load_environment_factory(
                    self.environment_factory_path,
                    distribution=self.source,
                    registration_label="Model registration",
                    kind=self.kind,
                    field_name="environment_factory",
                ),
            )
        return self._environment_factory

    def load_resource_capabilities(self) -> ResourceCapabilities:
        if self._resource_capabilities is _UNSET:
            object.__setattr__(
                self,
                "_resource_capabilities",
                load_instance(
                    self.resource_capabilities_path,
                    ResourceCapabilities,
                    registration_label="Model registration",
                    kind=self.kind,
                    field_name="resource_capabilities",
                ),
            )
        return self._resource_capabilities

    def load_probe(self) -> ResourceProbe | None:
        if self.probe_path is None:
            return None
        if self._probe is _UNSET:
            object.__setattr__(
                self,
                "_probe",
                load_callable(
                    self.probe_path,
                    registration_label="Model registration",
                    kind=self.kind,
                    field_name="probe",
                    reject_classes=True,
                ),
            )
        return self._probe
