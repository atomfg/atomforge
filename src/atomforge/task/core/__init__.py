__all__ = [
    "TaskSpec",
    "TaskResult",
    "TaskExecutor",
    "TaskCapabilitySpec",
    "ExecutionResources",
    "ResolvedResources",
]


def __getattr__(name: str):
    if name == "TaskSpec":
        from .spec import TaskSpec

        return TaskSpec
    if name == "TaskResult":
        from .result import TaskResult

        return TaskResult
    if name == "TaskExecutor":
        from .executor import TaskExecutor

        return TaskExecutor
    if name == "TaskCapabilitySpec":
        from .capability import TaskCapabilitySpec

        return TaskCapabilitySpec

    if name == "ExecutionResources":
        from .resources import ExecutionResources

        return ExecutionResources

    if name == "ResolvedResources":
        from .resources import ResolvedResources

        return ResolvedResources

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)
