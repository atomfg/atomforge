import pytest

from atomforge._host.backend.subprocess.backend import SubprocessBackend
from atomforge._core.env.env import EnvironmentSpec
from atomforge._builtins.model.ase_lj import LennardJones
from atomforge._core.property import Property
from atomforge._core.task.capability import TaskCapabilitySpec
from atomforge._runtime.registry.task.task_registry import TaskRegistry
from atomforge._builtins.task.bfgs import BFGS, BFGSExecutor, BFGSResult
from atomforge._builtins.task.singlepoint import SinglePoint
from atomforge._runtime.registry.task_registration import TaskRegistration


def test_task_registry_duplicate_kind_fails():
    registry = TaskRegistry()

    registration = TaskRegistration(
        spec_model=BFGS,
        result_model=BFGSResult,
        executor_class=BFGSExecutor,
        capability_spec=TaskCapabilitySpec(
            required=frozenset({Property.ENERGY, Property.FORCES}),
            optional=frozenset(),
        ),
        environment_factory=lambda spec: EnvironmentSpec(name=spec.kind),
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
    from atomforge._runtime.registry.task.task_helpers import ManifestToRegistrationConverter

    backend = SubprocessBackend()
    registration = backend._task_registry.get("bfgs")
    task = BFGS(structure=example_structure)

    assert registration.capability_spec.required == frozenset(
        {Property.ENERGY, Property.FORCES}
    )
    assert registration.capability_spec.optional == frozenset()
    assert registration.environment_factory(task) == EnvironmentSpec(
        name="bfgs", requirements=["ase"], provider_requirements=[ManifestToRegistrationConverter._resolve_distribution("atomforge")]
    )


def test_backend_resolves_task_environment_from_registration(example_structure):
    backend = SubprocessBackend()
    model = LennardJones()
    task = SinglePoint(structure=example_structure)

    registration = backend._task_registry.get(task.kind)
    task_env = registration.environment_factory(task)
    expected = (
        backend._model_registry.get(model.kind).environment_factory(model) + task_env
    )

    assert backend.setup_environment(model, task_env) == expected
