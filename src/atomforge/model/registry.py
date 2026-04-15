from dataclasses import dataclass

from atomforge.model.base import Model, ModelMetadata


@dataclass(frozen=True)
class ModelRegistration:
    model_class: type[Model]
    metadata: ModelMetadata


class ModelRegistry:
    def __init__(self) -> None:
        self._registrations: dict[str, ModelRegistration] = {}

    def register(
        self,
        model_kind: str,
        model_class: type[Model],
    ) -> None:
        if model_kind in self._registrations:
            raise ValueError(f"Model kind already registered: {model_kind}")

        self._registrations[model_kind] = ModelRegistration(
            model_class=model_class,
            metadata=model_class.metadata,
        )

    def get(self, model_kind: str) -> ModelRegistration:
        try:
            return self._registrations[model_kind]
        except KeyError as exc:
            raise KeyError(f"Unknown model kind: {model_kind}") from exc

    def __iter__(self):
        return iter(self._registrations.items())
