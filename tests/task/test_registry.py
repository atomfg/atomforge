import pytest

from atomforge.backend.subprocess.backend import SubprocessBackend
from atomforge_core.env.env import EnvironmentSpec
from atomforge_builtins.model.ase_lj import LennardJones
from atomforge_core.property import Property
from atomforge_core.task.capability import TaskCapabilitySpec
from atomforge_runtime.registry.task.task_registry import TaskRegistry
from atomforge_builtins.task.bfgs import BFGS, BFGSExecutor, BFGSResult
from atomforge_builtins.task.singlepoint import SinglePoint
from atomforge_runtime.registry.task_registration import TaskRegistration
from atomforge_core.registry.symbol_path import SymbolPath


def test_task_registry_duplicate_kind_fails():
    registry = TaskRegistry()

    registration = TaskRegistration(
        kind="bfgs",
        spec_model=BFGS,
        result_model_path=SymbolPath("atomforge_builtins.task.bfgs:BFGSResult"),
        executor_class_path=SymbolPath("atomforge_builtins.task.bfgs:BFGSExecutor"),
        capability_spec_path=SymbolPath(
            "atomforge_builtins.task.bfgs:BFGSCapabilitySpec"
        ),
        environment_factory_path=SymbolPath(
            "atomforge_builtins.task.bfgs:BFGSEnvironmentFactory"
        ),
        source=["atomforge-builtins"],
    )

    registry._register(
        registration,
        task_kind="bfgs",
    )

    with pytest.raises(ValueError):
        registry._register(
        registration,
        task_kind="bfgs",
    )



def test_builtin_registration_exposes_capabilities_and_environment(example_structure):
    backend = SubprocessBackend()
    registration = backend._task_registry.get("bfgs")
    task = BFGS(structure=example_structure)

    assert registration.load_capability_spec().required == frozenset(
        {Property.ENERGY, Property.FORCES}
    )
    assert registration.load_capability_spec().optional == frozenset()
    assert registration.load_environment_factory()(task) == EnvironmentSpec(
        name="bfgs", requirements=["ase"], provider_requirements=["atomforge-builtins"],
    )


def test_backend_resolves_task_environment_from_registration(example_structure):
    backend = SubprocessBackend()
    model = LennardJones()
    task = SinglePoint(structure=example_structure)

    registration = backend._task_registry.get(task.kind)
    task_env = registration.load_environment_factory()(task)
    expected = (
        backend._model_registry.get(model.kind).load_environment_factory()(model)
        + task_env
    )

    assert backend.setup_environment(model, task_env) == expected
