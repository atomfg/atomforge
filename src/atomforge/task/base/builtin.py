from atomforge.env.base.env import EnvironmentSpec
from atomforge.model.base.property import Property
from atomforge.task.base.capability import TaskCapabilitySpec
from atomforge.task.base.registry import TaskRegistry


def _register_single_point_task(registry: TaskRegistry) -> None:
    from atomforge.task.singlepoint import (
        SinglePointExecutor,
        SinglePointResult,
        SinglePoint,
    )

    registry.register(
        task_kind="single_point",
        spec_model=SinglePoint,
        result_model=SinglePointResult,
        executor_class=SinglePointExecutor,
        capability_spec=TaskCapabilitySpec(
            required=frozenset(),
            optional=frozenset({Property.ENERGY, Property.FORCES}),
        ),
        environment_factory=_single_point_environment,
    )


def _register_bfgs_task(registry: TaskRegistry) -> None:
    from atomforge.task.bfgs import (
        BFGSExecutor,
        BFGSResult,
        BFGS,
    )

    registry.register(
        task_kind="bfgs",
        spec_model=BFGS,
        result_model=BFGSResult,
        executor_class=BFGSExecutor,
        capability_spec=TaskCapabilitySpec(
            required=frozenset({Property.ENERGY, Property.FORCES}),
            optional=frozenset(),
        ),
        environment_factory=_bfgs_environment,
    )


def _single_point_environment(_spec) -> EnvironmentSpec:
    return EnvironmentSpec(name="single_point")


def _bfgs_environment(_spec) -> EnvironmentSpec:
    return EnvironmentSpec(name="bfgs", requirements=["ase"])


def register_builtin_tasks(registry: TaskRegistry) -> None:
    _register_single_point_task(registry)
    _register_bfgs_task(registry)


def get_default_task_registry() -> TaskRegistry:
    registry = TaskRegistry()
    register_builtin_tasks(registry)
    return registry
