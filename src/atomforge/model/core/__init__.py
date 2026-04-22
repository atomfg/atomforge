__all__ = [
    "Property",
    "ModelResult",
    "Reference",
    "ModelMetadata",
    "ModelSpec",
    "ModelExecutor",
    "ModelSpecT",
    "ResourceCapabilities",
]


def __getattr__(name: str):
    if name == "Property":
        from .property import Property

        return Property
    if name == "ModelResult":
        from .result import ModelResult

        return ModelResult
    if name == "Reference":
        from .metadata import Reference

        return Reference
    if name == "ModelMetadata":
        from .metadata import ModelMetadata

        return ModelMetadata
    if name == "ModelSpec":
        from .spec import ModelSpec

        return ModelSpec
    if name == "ModelExecutor":
        from .executor import ModelExecutor

        return ModelExecutor
    if name == "ModelSpecT":
        from .spec import ModelSpecT

        return ModelSpecT

    if name == "ResourceCapabilities":
        from .resource_caps import ResourceCapabilities

        return ResourceCapabilities
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)
