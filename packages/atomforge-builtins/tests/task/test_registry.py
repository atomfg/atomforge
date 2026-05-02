import pytest

from atomforge_core.env.env import EnvironmentSpec
from atomforge_core.property import Property
from atomforge_core.registry.symbol_path import SymbolPath
from atomforge_runtime.registry.task.task_registry import TaskRegistry
from atomforge_runtime.registry.task.task_registration import TaskRegistration

from atomforge_builtins.model.ase_lj import LennardJones
from atomforge_builtins.task.bfgs import BFGS
from atomforge_builtins.task.optimize import Optimize
from atomforge_builtins.task.single_point import SinglePoint


def test_task_registry_duplicate_kind_fails():
    registry = TaskRegistry()

    registration = TaskRegistration(
        kind="bfgs",
        spec_model=BFGS,
        result_model_path=SymbolPath("atomforge_builtins.task.bfgs.result:BFGSResult"),
        executor_class_path=SymbolPath(
            "atomforge_builtins.task.bfgs.executor:BFGSExecutor"
        ),
        capability_spec_path=SymbolPath(
            "atomforge_builtins.task.bfgs.definitions:BFGSCapabilitySpec"
        ),
        environment_factory_path=SymbolPath(
            "atomforge_builtins.task.bfgs.environment:BFGSEnvironmentFactory"
        ),
        source=["atomforge-builtins"],
    )

    registry._register(registration, task_kind="bfgs")

    with pytest.raises(ValueError):
        registry._register(registration, task_kind="bfgs")


def test_builtin_registration_exposes_capabilities_and_environment(example_structure):
    registry = TaskRegistry.default()
    registration = registry.get("bfgs")
    task = BFGS(structure=example_structure)

    assert registration.load_capability_spec().required == frozenset(
        {Property.ENERGY, Property.FORCES}
    )
    assert registration.load_capability_spec().optional == frozenset()
    assert registration.load_environment_factory()(task) == EnvironmentSpec(
        name="bfgs",
        requirements=["ase"],
        provider_requirements=["atomforge-builtins"],
    )


def test_model_and_task_environment_specs_merge(example_structure):
    task_registry = TaskRegistry.default()
    task_env = task_registry.get("single_point").load_environment_factory()(
        SinglePoint(structure=example_structure)
    )

    assert task_env == EnvironmentSpec(
        name="single_point",
        provider_requirements=["atomforge-builtins"],
    )
    assert LennardJones().kind == "ase-lj"


def test_optimize_registration_exposes_capabilities_and_environment(example_structure):
    registry = TaskRegistry.default()
    registration = registry.get("optimize")
    task = Optimize(structure=example_structure)

    assert registration.load_capability_spec().required == frozenset(
        {Property.ENERGY, Property.FORCES}
    )
    assert registration.load_capability_spec().optional == frozenset()
    assert registration.load_environment_factory()(task) == EnvironmentSpec(
        name="optimize",
        requirements=["ase"],
        provider_requirements=["atomforge-builtins"],
    )
