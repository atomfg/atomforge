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
        from .base import CommandResult

        return CommandResult
    if name == "CommandSpec":
        from .base import CommandSpec

        return CommandSpec
    if name == "EnvironmentHandle":
        from ..._core.env.env import EnvironmentHandle

        return EnvironmentHandle
    if name == "EnvironmentInfo":
        from ..._core.env.env import EnvironmentInfo

        return EnvironmentInfo
    if name == "EnvironmentProvider":
        from .base.provider import EnvironmentProvider

        return EnvironmentProvider
    if name == "EnvironmentSpec":
        from ..._core.env.env import EnvironmentSpec

        return EnvironmentSpec
    if name == "UVEnvironmentProvider":
        from .uv import UVEnvironmentProvider

        return UVEnvironmentProvider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)
