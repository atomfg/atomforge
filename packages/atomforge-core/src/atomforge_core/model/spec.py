"""The base class of model specs, and the roles of their fields.

Every field of a spec has one role:

- ``Variant``: chooses the trained parameters. The variant fields'
  values must be enumerable (``Literal``, ``bool``, and their unions with
  ``None``), so that a spec can list its variants.
- ``Setting``: everything else the executor uses, including what changes the
  numbers without changing the parameters.
- weights: the optional ``weights: LocalWeights | None`` field, recognised
  by its type. Declaring it is how a plugin says it loads local parameters.
- reserved: ``kind`` and ``environment_profile``, classified by name.

Mark a field with ``Annotated``::

    force_mode: Annotated[Literal["direct", "conservative"], Variant] = "direct"
    matmul_precision: Annotated[Literal["highest", "high"], Setting] = "highest"

A spec must bring every input to a canonical form: where a variant field has
no effect for some values of another, a ``mode="before"`` validator sets it
to ``None``, so that each trained model is one variant.
"""

from __future__ import annotations

import json
import types
from itertools import product
from typing import Any, Literal, TypeVar, Union, get_args, get_origin

from pydantic import BaseModel, ConfigDict, ValidationError

from atomforge_core.model.weights import LocalWeights


class FieldRole:
    """Marker for the role of a spec field, used in ``Annotated``."""

    __slots__ = ("name",)

    def __init__(self, name: str):
        self.name = name

    def __repr__(self) -> str:
        return self.name


Variant = FieldRole("Variant")
Setting = FieldRole("Setting")

RESERVED_FIELDS = frozenset({"kind", "environment_profile"})
WEIGHTS_FIELD = "weights"
DEFAULT_VARIANT_NAME = "default"


def _union_args(annotation: Any) -> tuple[Any, ...] | None:
    if get_origin(annotation) in (Union, types.UnionType):
        return get_args(annotation)
    return None


def enumerate_values(annotation: Any) -> tuple[Any, ...] | None:
    """Every value a variant field can take, or ``None`` if its type cannot be
    enumerated."""
    if annotation is bool:
        return (False, True)
    if annotation is type(None) or annotation is None:
        return (None,)
    if get_origin(annotation) is Literal:
        return get_args(annotation)
    args = _union_args(annotation)
    if args is not None:
        values: list[Any] = []
        for arg in args:
            arg_values = enumerate_values(arg)
            if arg_values is None:
                return None
            values.extend(v for v in arg_values if v not in values)
        return tuple(values)
    return None


def _mentions_local_weights(annotation: Any) -> bool:
    if annotation is LocalWeights:
        return True
    args = _union_args(annotation)
    return args is not None and LocalWeights in args


class ModelSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    environment_profile: str = "tested"

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        super().__pydantic_init_subclass__(**kwargs)
        problems = []
        for name, field in cls.model_fields.items():
            roles = [m for m in field.metadata if isinstance(m, FieldRole)]
            if name in RESERVED_FIELDS:
                if roles:
                    problems.append(f"{name} is reserved and takes no role marker")
                continue
            if _mentions_local_weights(field.annotation):
                if name != WEIGHTS_FIELD:
                    problems.append(
                        f"{name}: local weights must be the field named "
                        f"'{WEIGHTS_FIELD}'"
                    )
                elif roles:
                    problems.append(f"{name} needs no role marker")
                continue
            if len(roles) != 1:
                problems.append(
                    f"{name} needs exactly one role, Variant or Setting, "
                    f"as Annotated[<type>, Variant]; it has "
                    f"{roles or 'none'}"
                )
                continue
            if roles[0] is Variant and enumerate_values(field.annotation) is None:
                problems.append(
                    f"{name} is a Variant field, so its type must be "
                    f"enumerable (Literal, bool, or their unions with None), "
                    f"not {field.annotation!r}"
                )
        if problems:
            raise TypeError(
                f"{cls.__name__} has spec fields without a valid role:\n- "
                + "\n- ".join(problems)
            )

    # Roles

    @classmethod
    def _fields_with_role(cls, role: FieldRole) -> tuple[str, ...]:
        return tuple(
            name
            for name, field in cls.model_fields.items()
            if any(m is role for m in field.metadata)
        )

    @classmethod
    def variant_fields(cls) -> tuple[str, ...]:
        """The names of the variant fields, in field order."""
        return cls._fields_with_role(Variant)

    @classmethod
    def setting_fields(cls) -> tuple[str, ...]:
        return cls._fields_with_role(Setting)

    @classmethod
    def accepts_local_weights(cls) -> bool:
        return WEIGHTS_FIELD in cls.model_fields

    # Variants

    @classmethod
    def variants(cls: type[ModelSpecT]) -> tuple[ModelSpecT, ...]:
        """One spec per trained model, with default settings: the product of
        the variant fields' values, kept where it validates, without
        duplicates of the validated variant payload."""
        names = cls.variant_fields()
        values = [enumerate_values(cls.model_fields[name].annotation) for name in names]
        found: dict[str, ModelSpecT] = {}
        for combination in product(*values):
            try:
                spec = cls(**dict(zip(names, combination)))
            except ValidationError:
                continue
            key = json.dumps(spec.variant_payload(mode="json"), sort_keys=True)
            found.setdefault(key, spec)
        return tuple(found.values())

    @property
    def variant_name(self) -> str:
        """The variant fields' values joined by ``-`` in field order, ``None``
        left out; ``default`` for a spec without variant fields. A plugin may
        override it for nicer names."""
        values = [getattr(self, name) for name in self.variant_fields()]
        parts = [str(value) for value in values if value is not None]
        return "-".join(parts) or DEFAULT_VARIANT_NAME

    @property
    def variant_id(self) -> str:
        """``<kind>/<variant_name>``, with ``+local:<sha256[:8]>`` when the
        spec has local weights."""
        identifier = f"{getattr(self, 'kind', type(self).__name__)}/{self.variant_name}"
        weights = getattr(self, WEIGHTS_FIELD, None)
        if weights is not None:
            identifier += f"+local:{weights.short_sha256}"
        return identifier

    # Payloads

    def variant_payload(self, *, mode: str = "python") -> dict[str, Any]:
        return self.model_dump(mode=mode, include=set(self.variant_fields()))

    def settings_payload(self, *, mode: str = "python") -> dict[str, Any]:
        return self.model_dump(mode=mode, include=set(self.setting_fields()))

    def scientific_payload(self, *, mode: str = "python") -> dict[str, Any]:
        """What determines the numbers: kind, variant, settings, and the local
        weights' hash (not their path). Leaves out the environment
        profile."""
        payload = self.model_dump(
            mode=mode, exclude={"environment_profile", WEIGHTS_FIELD}
        )
        if self.accepts_local_weights():
            weights = getattr(self, WEIGHTS_FIELD)
            payload[WEIGHTS_FIELD] = None if weights is None else weights.sha256
        return payload


ModelSpecT = TypeVar("ModelSpecT", bound=ModelSpec)
