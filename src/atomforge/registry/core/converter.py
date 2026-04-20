from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from atomforge.registry.core.errors import RegistryCoreError
from atomforge.registry.core.helpers import (
    load_symbol,
    normalize_distribution_name,
    resolve_distribution,
    wrap_environment_factory,
)


class ManifestToRegistrationConverterBase(ABC):
    error_class = RegistryCoreError

    def _raise(self, message: str):
        raise self.error_class(message)

    def _load_symbol(self, dotted_path: str):
        try:
            return load_symbol(dotted_path)
        except (ImportError, AttributeError, ValueError) as exc:
            self._raise(f"Error loading module '{dotted_path}': {exc}")

    def _load_subclass(self, dotted_path: str, expected_type: type, label: str):
        symbol = self._load_symbol(dotted_path)
        if not issubclass(symbol, expected_type):
            self._raise(
                f"{label} '{dotted_path}' must be a subclass of {expected_type.__name__}"
            )
        return symbol

    def _load_instance(self, dotted_path: str, expected_type: type, label: str):
        symbol = self._load_symbol(dotted_path)
        if not isinstance(symbol, expected_type):
            self._raise(
                f"{label} '{dotted_path}' must be an instance of {expected_type.__name__}"
            )
        return symbol

    def _load_callable(
        self, dotted_path: str, label: str, *, reject_classes: bool = False
    ):
        symbol = self._load_symbol(dotted_path)
        if reject_classes and isinstance(symbol, type):
            self._raise(f"{label} '{dotted_path}' must be callable")
        if not callable(symbol):
            self._raise(f"{label} '{dotted_path}' must be callable")
        return symbol

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
    def _build_registration(self, manifest, components: dict[str, Any], environment_factory):
        raise NotImplementedError

    def convert(self, manifest, entry_point_name: str, entry_point_package: str):
        components = self._load_components(manifest)
        self._validate_distribution(manifest.distribution, entry_point_package)

        provider_requirements = [
            resolve_distribution(name) for name in manifest.distribution
        ]
        wrapped_environment_factory = wrap_environment_factory(
            components["environment_factory"], provider_requirements
        )

        registration = self._build_registration(
            manifest, components, wrapped_environment_factory
        )
        return registration, manifest.kind

    def __call__(self, manifest, entry_point_name: str, entry_point_package: str):
        return self.convert(manifest, entry_point_name, entry_point_package)
