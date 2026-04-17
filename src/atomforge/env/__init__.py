__all__ = [
    "CommandResult",
    "CommandSpec",
    "EnvironmentHandle",
    "EnvironmentInfo",
    "EnvironmentProvider",
    "EnvironmentSpec",
    "UVEnvironmentProvider",
]


def __getattr__(name: str):
    if name == "CommandResult":
        from .base.command import CommandResult

        return CommandResult
    if name == "CommandSpec":
        from .base.command import CommandSpec

        return CommandSpec
    if name == "EnvironmentHandle":
        from .base.env import EnvironmentHandle

        return EnvironmentHandle
    if name == "EnvironmentInfo":
        from .base.env import EnvironmentInfo

        return EnvironmentInfo
    if name == "EnvironmentProvider":
        from .base.provider import EnvironmentProvider

        return EnvironmentProvider
    if name == "EnvironmentSpec":
        from .base.env import EnvironmentSpec

        return EnvironmentSpec
    if name == "UVEnvironmentProvider":
        from .uv import UVEnvironmentProvider

        return UVEnvironmentProvider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)
