from __future__ import annotations

from atomforge_core.env.factory import EnvironmentFactory
from atomforge_core.registry.symbol_path import SymbolPath
from atomforge_runtime.registry.helpers import load_symbol


def _wrap_error(
    exc: Exception, *, registration_label: str, kind: str, field_name: str, path: object
) -> Exception:
    return type(exc)(
        f"{registration_label} '{kind}' failed to load {field_name} from '{path}': {exc}"
    )


def load_symbol_path(path: SymbolPath):
    try:
        return load_symbol(path)
    except (ImportError, AttributeError, ValueError) as exc:
        raise ValueError(f"Error loading module '{path}': {exc}") from exc


def load_subclass_path(path: SymbolPath, expected_type: type, label: str):
    symbol = load_symbol_path(path)
    if not issubclass(symbol, expected_type):
        raise TypeError(
            f"{label} '{path}' must be a subclass of {expected_type.__name__}"
        )
    return symbol


def load_instance_path(path: SymbolPath, expected_type: type, label: str):
    symbol = load_symbol_path(path)
    if not isinstance(symbol, expected_type):
        raise TypeError(
            f"{label} '{path}' must be an instance of {expected_type.__name__}"
        )
    return symbol


def load_callable_path(path: SymbolPath, label: str, *, reject_classes: bool = False):
    symbol = load_symbol_path(path)
    if reject_classes and isinstance(symbol, type):
        raise TypeError(f"{label} '{path}' must be callable")
    if not callable(symbol):
        raise TypeError(f"{label} '{path}' must be callable")
    return symbol


def build_environment_factory(path: SymbolPath, distribution: list[str], label: str):
    factory_class = load_subclass_path(path, EnvironmentFactory, label)
    return factory_class().with_provider_requirements(distribution)


def load_subclass(
    path: SymbolPath,
    expected_type: type,
    *,
    registration_label: str,
    kind: str,
    field_name: str,
):
    try:
        return load_subclass_path(path, expected_type, field_name)
    except (TypeError, ValueError, ImportError, AttributeError) as exc:
        raise _wrap_error(
            exc,
            registration_label=registration_label,
            kind=kind,
            field_name=field_name,
            path=path,
        ) from exc


def load_instance(
    path: SymbolPath,
    expected_type: type,
    *,
    registration_label: str,
    kind: str,
    field_name: str,
):
    try:
        return load_instance_path(path, expected_type, field_name)
    except (TypeError, ValueError, ImportError, AttributeError) as exc:
        raise _wrap_error(
            exc,
            registration_label=registration_label,
            kind=kind,
            field_name=field_name,
            path=path,
        ) from exc


def load_callable(
    path: SymbolPath,
    *,
    registration_label: str,
    kind: str,
    field_name: str,
    reject_classes: bool = False,
):
    try:
        return load_callable_path(path, field_name, reject_classes=reject_classes)
    except (TypeError, ValueError, ImportError, AttributeError) as exc:
        raise _wrap_error(
            exc,
            registration_label=registration_label,
            kind=kind,
            field_name=field_name,
            path=path,
        ) from exc


def load_environment_factory(
    path: SymbolPath,
    *,
    distribution: list[str],
    registration_label: str,
    kind: str,
    field_name: str,
):
    try:
        return build_environment_factory(path, distribution, field_name)
    except (TypeError, ValueError, ImportError, AttributeError) as exc:
        raise _wrap_error(
            exc,
            registration_label=registration_label,
            kind=kind,
            field_name=field_name,
            path=path,
        ) from exc
