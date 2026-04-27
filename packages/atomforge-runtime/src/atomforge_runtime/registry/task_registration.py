from dataclasses import dataclass, field
from typing import Generic

from atomforge_core.task.capability import TaskCapabilitySpec
from atomforge_core.task.executor import TaskExecutor
from atomforge_core.task.result import TaskResult
from atomforge_core.task.result import TaskResultT
from atomforge_core.task.spec import TaskSpecT
from atomforge_core.env.factory import EnvironmentFactory

from atomforge_core.registry.symbol_path import SymbolPath
from atomforge_runtime.registry.loading import (
    load_environment_factory,
    load_instance,
    load_subclass,
)

_UNSET = object()  # Sentinel for unset values

@dataclass(frozen=True)
class TaskRegistration(Generic[TaskSpecT, TaskResultT]):
    kind: str
    spec_model: type[TaskSpecT]
    result_model_path: SymbolPath
    executor_class_path: SymbolPath
    capability_spec_path: SymbolPath
    environment_factory_path: SymbolPath
    source: list[str]

    _result_model: object = field(default=_UNSET, init=False, repr=False, compare=False)
    _executor_class: object = field(default=_UNSET, init=False, repr=False, compare=False)
    _capability_spec: object = field(
        default=_UNSET, init=False, repr=False, compare=False
    )
    _environment_factory: object = field(
        default=_UNSET, init=False, repr=False, compare=False
    )

    def load_result_model(self) -> type[TaskResultT]:
        if self._result_model is _UNSET:
            object.__setattr__(
                self,
                "_result_model",
                load_subclass(
                    self.result_model_path,
                    TaskResult,
                    registration_label="Task registration",
                    kind=self.kind,
                    field_name="result_model",
                ),
            )
        return self._result_model

    def load_executor_class(self) -> type[TaskExecutor[TaskSpecT, TaskResultT]]:
        if self._executor_class is _UNSET:
            object.__setattr__(
                self,
                "_executor_class",
                load_subclass(
                    self.executor_class_path,
                    TaskExecutor,
                    registration_label="Task registration",
                    kind=self.kind,
                    field_name="executor_class",
                ),
            )
        return self._executor_class

    def load_capability_spec(self) -> TaskCapabilitySpec:
        if self._capability_spec is _UNSET:
            object.__setattr__(
                self,
                "_capability_spec",
                load_instance(
                    self.capability_spec_path,
                    TaskCapabilitySpec,
                    registration_label="Task registration",
                    kind=self.kind,
                    field_name="capability_spec",
                ),
            )
        return self._capability_spec

    def load_environment_factory(self) -> EnvironmentFactory[TaskSpecT]:
        if self._environment_factory is _UNSET:
            object.__setattr__(
                self,
                "_environment_factory",
                load_environment_factory(
                    self.environment_factory_path,
                    distribution=self.source,
                    registration_label="Task registration",
                    kind=self.kind,
                    field_name="environment_factory",
                ),
            )
        return self._environment_factory
