import pytest

from atomforge_core.registry.task_manifest import TaskManifest
from atomforge_runtime.registry.task.task_helpers import (
    ManifestToRegistrationConverter,
    TaskRegistryError,
)
from atomforge_runtime.registry.task_registration import TaskRegistration

from runtime_fakes import FakeTask


def manifest_factory(
    kind="fake-task",
    executor_cls="runtime_fakes:FakeTaskExecutor",
    spec_model="runtime_fakes:FakeTask",
    result_model="runtime_fakes:FakeTaskResult",
    capability_spec="runtime_fakes:FakeCapabilitySpec",
    environment_factory_cls="runtime_fakes:FakeEnvironmentFactory",
    distribution=["runtime-test-plugin"],
):
    return TaskManifest(
        kind=kind,
        spec_model=spec_model,
        executor_cls=executor_cls,
        result_model=result_model,
        capability_spec=capability_spec,
        environment_factory_cls=environment_factory_cls,
        distribution=distribution,
    )


def test_manifest_to_registration_converter():
    manifest = manifest_factory()
    converter = ManifestToRegistrationConverter()
    registration, kind = converter(
        manifest,
        entry_point_name="test_registration",
        entry_point_package="runtime-test-plugin",
    )
    assert isinstance(registration, TaskRegistration)
    assert kind == "fake-task"


def test_converter_invalid_spec():
    manifest = manifest_factory(spec_model="runtime_fakes:FakeMetadata")
    converter = ManifestToRegistrationConverter()
    with pytest.raises(TaskRegistryError):
        converter(
            manifest,
            entry_point_name="test_spec",
            entry_point_package="runtime-test-plugin",
        )


def test_converter_invalid_executor():
    manifest = manifest_factory(executor_cls="runtime_fakes:FakeMetadata")
    converter = ManifestToRegistrationConverter()
    registration, _ = converter(
        manifest,
        entry_point_name="test_executor",
        entry_point_package="runtime-test-plugin",
    )
    with pytest.raises((ImportError, ValueError, TypeError, AttributeError)):
        registration.load_executor_class()


def test_converter_invalid_result():
    manifest = manifest_factory(result_model="runtime_fakes:FakeMetadata")
    converter = ManifestToRegistrationConverter()
    registration, _ = converter(
        manifest,
        entry_point_name="test_result",
        entry_point_package="runtime-test-plugin",
    )
    with pytest.raises((TypeError, ValueError)):
        registration.load_result_model()


def test_converter_invalid_capability_spec():
    manifest = manifest_factory(capability_spec="runtime_fakes:FakeMetadata")
    converter = ManifestToRegistrationConverter()
    registration, _ = converter(
        manifest,
        entry_point_name="test_capability_spec",
        entry_point_package="runtime-test-plugin",
    )
    with pytest.raises((TypeError, ValueError)):
        registration.load_capability_spec()


def test_converter_wrapped_environment_factory(example_structure):
    manifest = manifest_factory()
    converter = ManifestToRegistrationConverter()
    registration, _ = converter(
        manifest,
        entry_point_name="test_environment_factory",
        entry_point_package="runtime-test-plugin",
    )
    environment_factory = registration.load_environment_factory()
    example_task_spec = FakeTask(structure=example_structure)
    env_spec = environment_factory(example_task_spec)

    assert env_spec.provider_requirements == ("runtime-test-plugin",)


def test_task_registration_validate_strict_warms_cache():
    manifest = manifest_factory()
    converter = ManifestToRegistrationConverter()
    registration, _ = converter(
        manifest,
        entry_point_name="test_validate_strict",
        entry_point_package="runtime-test-plugin",
    )

    registration.validate_strict()

    result_model = registration.load_result_model()
    registration.validate_strict()

    assert result_model is registration.load_result_model()

