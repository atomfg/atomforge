from __future__ import annotations

from typing_extensions import Self

from atomforge_runtime.registry.strict import (
    RegistryStrictValidationError,
    StrictValidationFailure,
)


class EntryPointRegistryBase:
    entry_point_group: str
    manifest_type: type
    converter: callable
    kind_label: str

    def __init__(self) -> None:
        self._registrations = {}

    def _register(self, registration, kind: str) -> None:
        if kind in self._registrations:
            raise ValueError(f"{self.kind_label} already registered: {kind}")
        self._registrations[kind] = registration

    def get(self, kind: str):
        try:
            return self._registrations[kind]
        except KeyError as exc:
            raise KeyError(f"Unknown {self.kind_label}: {kind}") from exc

    def __iter__(self):
        return iter(self._registrations.items())

    def _load_entry_points(self) -> None:
        from importlib.metadata import entry_points

        eps = entry_points(group=self.entry_point_group)
        entry_point_packages: dict[str, str] = {}

        for ep in eps:
            manifest = ep.load()

            if not isinstance(manifest, self.manifest_type):
                raise TypeError(
                    f"Entry point '{ep.name}' must be a {self.manifest_type.__name__} instance"
                )

            registration, kind = self.converter(
                manifest, entry_point_name=ep.name, entry_point_package=ep.dist.name
            )

            if kind in self._registrations:
                raise ValueError(
                    f"{self.kind_label} already registered: {ep.name} (from {ep.dist.name} and {entry_point_packages[kind]})"
                )

            self._register(registration, kind)
            entry_point_packages[kind] = ep.dist.name

    def _collect_registration_strict_failures(
        self, registration
    ) -> list[StrictValidationFailure]:
        collect_checks = getattr(registration, "_strict_validation_entries", None)
        if collect_checks is None:
            registration.validate_strict()
            return []

        failures = []
        for field_name, path, loader in collect_checks():
            try:
                loader()
            except Exception as exc:
                failures.append(
                    StrictValidationFailure(
                        kind_label=self.kind_label,
                        registration_kind=registration.kind,
                        field_name=field_name,
                        path=None if path is None else str(path),
                        message=str(exc),
                    )
                )
        return failures

    @classmethod
    def default(cls) -> Self:
        instance = cls()
        instance._load_entry_points()
        return instance

    @classmethod
    def strict(cls) -> Self:
        instance = cls.default()
        failures = []
        for _, registration in instance:
            failures.extend(instance._collect_registration_strict_failures(registration))
        if failures:
            raise RegistryStrictValidationError(failures)
        return instance
