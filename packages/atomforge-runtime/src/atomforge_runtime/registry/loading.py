from __future__ import annotations

from atomforge_core.registry.symbol_path import SymbolPath
from atomforge_runtime.registry.base_converter import ManifestToRegistrationConverterBase


def _wrap_error(
    exc: Exception, *, registration_label: str, kind: str, field_name: str, path: object
) -> Exception:
    return type(exc)(
        f"{registration_label} '{kind}' failed to load {field_name} from '{path}': {exc}"
    )


def load_subclass(
    path: SymbolPath,
    expected_type: type,
    *,
    registration_label: str,
    kind: str,
    field_name: str,
):
    try:
        return ManifestToRegistrationConverterBase.load_subclass_path(
            path, expected_type, field_name
        )
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
        return ManifestToRegistrationConverterBase.load_instance_path(
            path, expected_type, field_name
        )
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
        return ManifestToRegistrationConverterBase.load_callable_path(
            path, field_name, reject_classes=reject_classes
        )
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
        return ManifestToRegistrationConverterBase.build_environment_factory(
            path, distribution, field_name
        )
    except (TypeError, ValueError, ImportError, AttributeError) as exc:
        raise _wrap_error(
            exc,
            registration_label=registration_label,
            kind=kind,
            field_name=field_name,
            path=path,
        ) from exc
