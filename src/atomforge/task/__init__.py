__all__ = ["Task", "SinglePoint"]


def __getattr__(name: str):
    if name == "Task":
        from .base import Task

        return Task
    if name == "SinglePoint":
        from .singlepoint import SinglePoint

        return SinglePoint
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
