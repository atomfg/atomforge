from atomforge.task.base.registry import TaskRegistry


def _register_single_point_task(registry: TaskRegistry) -> None:
    from atomforge.task.singlepoint import (
        SinglePointExecutor,
        SinglePointResult,
        SinglePointSpec,
    )

    registry.register(
        task_kind="single_point",
        spec_model=SinglePointSpec,
        result_model=SinglePointResult,
        executor=SinglePointExecutor(),
    )

def _register_bfgs_task(registry: TaskRegistry) -> None:
    from atomforge.task.bfgs import (
        BFGSExecutor,
        BFGSResult,
        BFGSSpec,
    )

    registry.register(
        task_kind="bfgs",
        spec_model=BFGSSpec,
        result_model=BFGSResult,
        executor=BFGSExecutor(),
    )


def register_builtin_tasks(registry: TaskRegistry) -> None:
    _register_single_point_task(registry)
    _register_bfgs_task(registry)


def get_default_task_registry() -> TaskRegistry:
    registry = TaskRegistry()
    register_builtin_tasks(registry)
    return registry
