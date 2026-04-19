__all__ = [
    "TaskRegistration",
    "TaskRegistry",
    "register_builtin_tasks",
    "get_default_task_registry",
]


def __getattr__(name: str):
    if name == "TaskRegistration":
        from .registry import TaskRegistration

        return TaskRegistration
    if name == "TaskRegistry":
        from .registry import TaskRegistry

        return TaskRegistry
    if name == "register_builtin_tasks":
        from .builtin import register_builtin_tasks

        return register_builtin_tasks
    if name == "get_default_task_registry":
        from .builtin import get_default_task_registry

        return get_default_task_registry
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)
