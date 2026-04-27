from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from atomforge_core.registry.errors import RegistryCoreError
from atomforge_core.registry.symbol_path import SymbolPath
from atomforge_runtime.registry.helpers import (
    load_symbol,
    normalize_distribution_name,
    resolve_distribution,
)

from atomforge_core.env.factory import EnvironmentFactory


class ManifestToRegistrationConverterBase(ABC):
    error_class = RegistryCoreError

    def _raise(self, message: str):
        raise self.error_class(message)

    @staticmethod
    def load_symbol_path(path: SymbolPath):
        try:
            return load_symbol(path)
        except (ImportError, AttributeError, ValueError) as exc:
            raise ValueError(f"Error loading module '{path}': {exc}") from exc

    @classmethod
    def load_subclass_path(
        cls, path: SymbolPath, expected_type: type, label: str
    ):
        symbol = cls.load_symbol_path(path)
        if not issubclass(symbol, expected_type):
            raise TypeError(
                f"{label} '{path}' must be a subclass of {expected_type.__name__}"
            )
        return symbol

    @classmethod
    def load_instance_path(
        cls, path: SymbolPath, expected_type: type, label: str
    ):
        symbol = cls.load_symbol_path(path)
        if not isinstance(symbol, expected_type):
            raise TypeError(
                f"{label} '{path}' must be an instance of {expected_type.__name__}"
            )
        return symbol

    @classmethod
    def load_callable_path(
        cls, path: SymbolPath, label: str, *, reject_classes: bool = False
    ):
        symbol = cls.load_symbol_path(path)
        if reject_classes and isinstance(symbol, type):
            raise TypeError(f"{label} '{path}' must be callable")
        if not callable(symbol):
            raise TypeError(f"{label} '{path}' must be callable")
        return symbol

    @classmethod
    def build_environment_factory(
        cls, path: SymbolPath, distribution: list[str], label: str
    ) -> EnvironmentFactory:
        factory_class = cls.load_subclass_path(path, EnvironmentFactory, label)
        return factory_class().with_provider_requirements(distribution)

    def _load_symbol(self, dotted_path: SymbolPath):
        try:
            return self.load_symbol_path(dotted_path)
        except (TypeError, ValueError) as exc:
            self._raise(str(exc))

    def _load_subclass(self, dotted_path: SymbolPath, expected_type: type, label: str):
        try:
            return self.load_subclass_path(dotted_path, expected_type, label)
        except (TypeError, ValueError) as exc:
            self._raise(str(exc))

    def _load_instance(self, dotted_path: SymbolPath, expected_type: type, label: str):
        try:
            return self.load_instance_path(dotted_path, expected_type, label)
        except (TypeError, ValueError) as exc:
            self._raise(str(exc))

    def _load_callable(
        self, dotted_path: SymbolPath, label: str, *, reject_classes: bool = False
    ):
        try:
            return self.load_callable_path(
                dotted_path, label, reject_classes=reject_classes
            )
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
