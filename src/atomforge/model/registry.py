from dataclasses import dataclass

from atomforge.model.base import (
    ModelMetadata,
    ModelExecutor,
    Property,
    ModelSpecT,
    EnvironmentFactory
)

from typing import Generic


@dataclass(frozen=True)
class ModelRegistration(Generic[ModelSpecT]):
    model_spec: type[ModelSpecT]
    metadata: ModelMetadata
    executor_class: type[ModelExecutor[ModelSpecT]]
    supported_properties: frozenset[Property]
    environment_factory: EnvironmentFactory[ModelSpecT]


class ModelRegistry:
    def __init__(self) -> None:
        self._registrations: dict[str, ModelRegistration] = {}

    def register(
        self,
        model_kind: str,
        model_spec: type[ModelSpecT],
        executor_class: type[ModelExecutor[ModelSpecT]],
        supported_properties: frozenset[Property],
        environment_factory: EnvironmentFactory[ModelSpecT],
        metadata: ModelMetadata,
    ) -> None:
        if model_kind in self._registrations:
            raise ValueError(f"Model kind already registered: {model_kind}")

        self._registrations[model_kind] = ModelRegistration(
            model_spec=model_spec,
            metadata=metadata,
            executor_class=executor_class,
            supported_properties=supported_properties,
            environment_factory=environment_factory,
        )

    def get(self, model_kind: str) -> ModelRegistration:
        try:
            return self._registrations[model_kind]
        except KeyError as exc:
            raise KeyError(f"Unknown model kind: {model_kind}") from exc

    def __iter__(self):
        return iter(self._registrations.items())
