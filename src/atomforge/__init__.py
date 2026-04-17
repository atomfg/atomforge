__all__ = ["Structure"]


def __getattr__(name: str):
    if name == "Structure":
        from .structure import Structure

        return Structure
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)
