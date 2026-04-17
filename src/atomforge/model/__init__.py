__all__ = [
    "ModelSpec",
    "ModelResult",
    "Property",
    "ModelRegistry",
    "get_default_model_registry",
]


def __getattr__(name: str):
    if name == "ModelSpec":
        from .base.spec import ModelSpec

        return ModelSpec
    if name == "ModelResult":
        from .base.result import ModelResult

        return ModelResult
    if name == "Property":
        from .base.property import Property

        return Property
    if name == "ModelRegistry":
        from .registry import ModelRegistry

        return ModelRegistry
    if name == "get_default_model_registry":
        from .builtin import get_default_model_registry

        return get_default_model_registry
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)
