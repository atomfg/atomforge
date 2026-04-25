__all__ = ["SinglePoint", "BFGS"]


def __getattr__(name: str):
    if name == "SinglePoint":
        from .singlepoint import SinglePoint

        return SinglePoint
    if name == "BFGS":
        from .bfgs import BFGS

        return BFGS
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)
