from dataclasses import dataclass, field
from collections.abc import Callable
from typing import Generic

from atomforge_core.env.factory import EnvironmentFactory
from atomforge_core.model.executor import ModelExecutor
from atomforge_core.model.metadata import ModelMetadata, VariantInfo
from atomforge_core.property import Property
from atomforge_core.resources.resource_caps import ResourceCapabilities
from atomforge_core.model.spec import ModelSpecT
from atomforge_core.resources.resource_probes import ResourceProbe
from atomforge_core.registry.symbol_path import SymbolPath
from atomforge_core.task.executor import TaskExecutor
from atomforge_core.model.declarations import (
    check_resource_capabilities,
    check_supported_properties,
    is_per_variant,
    kind_declaration,
    resolve_declaration,
    union_resource_capabilities,
    union_supported_properties,
)
from atomforge_runtime.registry.loading import (
    load_callable,
    load_environment_factory,
    load_instance,
    load_subclass,
    load_symbol_path,
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
    variant_info_path: SymbolPath | None = None
    source: list[str] = field(default_factory=list)
    task_overrides: dict[str, SymbolPath] = field(default_factory=dict)

    _metadata: object = field(default=_UNSET, init=False, repr=False, compare=False)
    _executor_class: object = field(
        default=_UNSET, init=False, repr=False, compare=False
    )
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
    _variant_info: object = field(default=_UNSET, init=False, repr=False, compare=False)

    _task_override_executors: object = field(
        default=_UNSET, init=False, repr=False, compare=False
    )

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

    def _load_declaration(self, attr: str, path: SymbolPath, field_name: str, check):
        """The manifest's value or function of the spec, loaded once."""
        if getattr(self, attr) is _UNSET:
            try:
                declaration = load_symbol_path(path)
                if not is_per_variant(declaration):
                    check(declaration)
            except (TypeError, ValueError) as exc:
                raise type(exc)(
                    f"Model registration '{self.kind}' failed to load {field_name} "
                    f"from '{path}': {exc}"
                ) from exc
            object.__setattr__(self, attr, declaration)
        return getattr(self, attr)

    def _declaration_for(self, declaration, spec, field_name: str, check, union):
        try:
            if spec is None:
                return kind_declaration(declaration, self.model_spec, check, union)
            return resolve_declaration(declaration, spec, check)
        except (TypeError, ValueError) as exc:
            target = "the kind" if spec is None else f"'{spec.variant_id}'"
            raise type(exc)(
                f"Model registration '{self.kind}' failed to declare {field_name} "
                f"for {target}: {exc}"
            ) from exc

    def load_supported_properties(
        self, spec: ModelSpecT | None = None
    ) -> frozenset[Property]:
        """The properties ``spec`` supports or, without a spec, those that
        some variant of the kind supports."""
        declaration = self._load_declaration(
            "_supported_properties",
            self.supported_properties_path,
            "supported_properties",
            check_supported_properties,
        )
        return self._declaration_for(
            declaration,
            spec,
            "supported_properties",
            check_supported_properties,
            union_supported_properties,
        )

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

    def load_resource_capabilities(
        self, spec: ModelSpecT | None = None
    ) -> ResourceCapabilities:
        """The resources ``spec`` supports or, without a spec, the union over
        the variants of the kind."""
        declaration = self._load_declaration(
            "_resource_capabilities",
            self.resource_capabilities_path,
            "resource_capabilities",
            check_resource_capabilities,
        )
        return self._declaration_for(
            declaration,
            spec,
            "resource_capabilities",
            check_resource_capabilities,
            union_resource_capabilities,
        )

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

    def load_variant_info(self) -> Callable[[ModelSpecT], VariantInfo] | None:
        """The manifest's ``variant_info`` callable, or None if it has none."""
        if self.variant_info_path is None:
            return None
        if self._variant_info is _UNSET:
            object.__setattr__(
                self,
                "_variant_info",
                load_callable(
                    self.variant_info_path,
                    registration_label="Model registration",
                    kind=self.kind,
                    field_name="variant_info",
                    reject_classes=True,
                ),
            )
        return self._variant_info

    def check_task_override(self, task_kind: str) -> bool:
        return task_kind in self.task_overrides

    def load_task_override_executor_class(
        self, task_kind: str
    ) -> type[TaskExecutor] | None:
        if task_kind not in self.task_overrides:
            return None
        if self._task_override_executors is _UNSET:
            object.__setattr__(self, "_task_override_executors", {})
        if task_kind not in self._task_override_executors:
            object.__setattr__(
                self,
                "_task_override_executors",
                {
                    **self._task_override_executors,
                    task_kind: load_subclass(
                        self.task_overrides[task_kind],
                        TaskExecutor,
                        registration_label="Model registration",
                        kind=self.kind,
                        field_name=f"task_overrides[{task_kind}]",
                    ),
                },
            )
        return self._task_override_executors.get(task_kind, None)

    def load_all_task_override_executors(self) -> dict[str, type[TaskExecutor]]:
        executors = {}
        for task_kind in self.task_overrides.keys():
            executors[task_kind] = self.load_task_override_executor_class(task_kind)
        return executors

    def _strict_validation_entries(self):
        return [
            ("metadata", self.metadata_path, self.load_metadata),
            ("executor_class", self.executor_class_path, self.load_executor_class),
            (
                "supported_properties",
                self.supported_properties_path,
                self.load_supported_properties,
            ),
            (
                "environment_factory",
                self.environment_factory_path,
                self.load_environment_factory,
            ),
            (
                "resource_capabilities",
                self.resource_capabilities_path,
                self.load_resource_capabilities,
            ),
            ("probe", self.probe_path, self.load_probe),
            (
                "task_override_executors",
                self.task_overrides,
                self.load_all_task_override_executors,
            ),
        ]

    def validate_strict(self) -> None:
        for _, _, loader in self._strict_validation_entries():
            loader()
