from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from atomforge_core.registry.errors import RegistryCoreError
from atomforge_core.registry.symbol_path import SymbolPath
from atomforge_runtime.registry.helpers import normalize_distribution_name
from atomforge_runtime.registry.loading import load_subclass_path


class ManifestToRegistrationConverterBase(ABC):
    error_class = RegistryCoreError

    def _raise(self, message: str):
        raise self.error_class(message)

    def _load_subclass(self, dotted_path: SymbolPath, expected_type: type, label: str):
        try:
            return load_subclass_path(dotted_path, expected_type, label)
        except (TypeError, ValueError) as exc:
            self._raise(str(exc))

    def _validate_distribution(
        self, manifest_distribution: list[str], entry_point_package: str
    ) -> None:
        if normalize_distribution_name(entry_point_package) not in {
            normalize_distribution_name(name) for name in manifest_distribution
        }:
            self._raise(
                f"Entry point package '{entry_point_package}' must be listed in the manifest's distribution field"
            )

    @abstractmethod
    def _load_components(self, manifest) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def _build_registration(
        self,
        manifest,
        components: dict[str, Any],
    ):
        raise NotImplementedError

    def convert(self, manifest, entry_point_name: str, entry_point_package: str):
        components = self._load_components(manifest)
        self._validate_distribution(manifest.distribution, entry_point_package)
        registration = self._build_registration(manifest, components)
        return registration, manifest.kind

    def __call__(self, manifest, entry_point_name: str, entry_point_package: str):
        return self.convert(manifest, entry_point_name, entry_point_package)
