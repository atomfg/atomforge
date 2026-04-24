__all__ = [
    "ModelSpec",
    "ModelResult",
    "Property",
]


def __getattr__(name: str):
    if name == "ModelSpec":
        from ..._core.model.spec import ModelSpec

        return ModelSpec
    if name == "ModelResult":
        from ..._core.model.result import ModelResult

        return ModelResult
    if name == "Property":
        from ..._core.property import Property

        return Property

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)
