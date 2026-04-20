from typing import Self

from atomforge.registry.model.helpers import manifest_to_registration
from atomforge.registry.model.manifest import ModelManifest
from atomforge.registry.model.registration import ModelRegistration


class ModelRegistry:
    def __init__(self) -> None:
        self._registrations: dict[str, ModelRegistration] = {}

    def _register(self, registration: ModelRegistration, model_kind: str) -> None:
        if model_kind in self._registrations:
            raise ValueError(f"Model kind already registered: {model_kind}")

        self._registrations[model_kind] = registration

    def get(self, model_kind: str) -> ModelRegistration:
        try:
            return self._registrations[model_kind]
        except KeyError as exc:
            raise KeyError(f"Unknown model kind: {model_kind}") from exc

    def __iter__(self):
        return iter(self._registrations.items())

    def _load_entry_points(self) -> None:
        from importlib.metadata import entry_points

        eps = entry_points(group="atomforge.model")
        entry_point_packages: dict[str, str] = {}

        for ep in eps:
            manifest = ep.load()

            if not isinstance(manifest, ModelManifest):
                raise TypeError(
                    f"Entry point '{ep.name}' must be a ModelManifest instance"
                )

            registration, kind = manifest_to_registration(
                manifest, entry_point_name=ep.name, entry_point_package=ep.dist.name
            )

            if kind in self._registrations:
                raise ValueError(
                    f"Model kind already registered: {ep.name} (from {ep.dist.name} and {entry_point_packages[kind]})"
                )

            self._register(registration, kind)
            entry_point_packages[kind] = ep.dist.name

    @classmethod
    def default(cls) -> Self:
        instance = cls()
        instance._load_entry_points()
        return instance
