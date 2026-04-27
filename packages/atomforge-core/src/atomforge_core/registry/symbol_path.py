from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from importlib.util import find_spec
from typing import Any

from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic_core import CoreSchema, PydanticCustomError, core_schema


@dataclass(frozen=True, slots=True)
class SymbolPath:
    """
    Immutable value object for import paths of the form:

        "package.module:Symbol"
    """

    raw: str
    _module_path: str = field(init=False, repr=False)
    _attribute_name: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.raw, str):
            raise TypeError("SymbolPath must be built from a string")

        module_path, attribute_name = self._parse(self.raw)
        object.__setattr__(self, "_module_path", module_path)
        object.__setattr__(self, "_attribute_name", attribute_name)

    @staticmethod
    def _parse(value: str) -> tuple[str, str]:
        value = value.strip()
        if not value:
            raise ValueError("SymbolPath cannot be empty")

        if value.count(":") != 1:
            raise ValueError(
                "SymbolPath must be of the form 'package.module:attribute'"
            )

        module_path, attribute_name = value.split(":", 1)

        if not module_path:
            raise ValueError("SymbolPath is missing the module path before ':'")
        if not attribute_name:
            raise ValueError("SymbolPath is missing the attribute name after ':'")

        # Keep validation intentionally moderate:
        # require dotted identifiers for the module path.
        module_parts = module_path.split(".")
        if any(not part for part in module_parts):
            raise ValueError(f"Invalid module path in SymbolPath: {module_path!r}")
        if any(not part.isidentifier() for part in module_parts):
            raise ValueError(f"Invalid module path in SymbolPath: {module_path!r}")

        # Allow dotted attribute access like "Outer.Inner" if you want nested attrs.
        attr_parts = attribute_name.split(".")
        if any(not part for part in attr_parts):
            raise ValueError(f"Invalid attribute path in SymbolPath: {attribute_name!r}")
        if any(not part.isidentifier() for part in attr_parts):
            raise ValueError(f"Invalid attribute path in SymbolPath: {attribute_name!r}")

        return module_path, attribute_name

    @property
    def module_path(self) -> str:
        return self._module_path

    @property
    def attribute_name(self) -> str:
        return self._attribute_name

    def module_is_discoverable(self) -> bool:
        try:
            return find_spec(self.module_path) is not None
        except (ImportError, ValueError, ModuleNotFoundError):
            return False

    def require_module_discoverable(self) -> None:
        if not self.module_is_discoverable():
            raise ImportError(f"Module {self.module_path!r} is not discoverable")

    def load_symbol(self) -> Any:
        """
        Import the module and resolve the attribute path.

        Supports dotted attribute names, e.g.
            'package.module:Outer.Inner'
        """
        try:
            module = import_module(self.module_path)
        except Exception as exc:
            raise ImportError(
                f"Failed to import module {self.module_path!r} for {self.raw!r}: {exc}"
            ) from exc

        obj: Any = module
        for part in self.attribute_name.split("."):
            try:
                obj = getattr(obj, part)
            except AttributeError as exc:
                raise AttributeError(
                    f"Module path {self.module_path!r} does not define "
                    f"attribute path {self.attribute_name!r} for {self.raw!r}"
                ) from exc

        return obj

    def __str__(self) -> str:
        return self.raw

    @classmethod
    def _coerce(cls, value: Any) -> SymbolPath:
        if isinstance(value, cls):
            return value
        if not isinstance(value, str):
            raise PydanticCustomError(
                "symbol_path_type",
                "Input should be a string or SymbolPath instance",
            )
        try:
            return cls(value)
        except (TypeError, ValueError) as exc:
            raise PydanticCustomError(
                "symbol_path_format",
                str(exc),
            ) from exc

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: type[Any],
        handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        return core_schema.no_info_plain_validator_function(
            cls._coerce,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda value: value.raw,
                return_schema=core_schema.str_schema(),
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> dict[str, Any]:
        json_schema = handler(core_schema)
        json_schema.update(
            {
                "type": "string",
                "title": "SymbolPath",
                "examples": [
                    "my_plugin.model:ModelSpec",
                    "my_plugin.executor:MyExecutor",
                ],
            }
        )
        return json_schema
