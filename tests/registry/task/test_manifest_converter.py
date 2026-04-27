import pytest
from atomforge_runtime.registry.task.task_helpers import ManifestToRegistrationConverter, TaskRegistryError
from atomforge_runtime.registry.task_registration import TaskRegistration

def test_manifest_to_registration_converter(manifest_factory):
    manifest = manifest_factory()
    converter = ManifestToRegistrationConverter()
    registration, kind = converter(manifest, entry_point_name="test_registration", entry_point_package="atomforge")
    assert isinstance(registration, TaskRegistration)

def test_converter_invalid_spec(manifest_factory):
    manifest = manifest_factory(spec_model="atomforge.registry.task.manifest:TaskManifest")  # Using TaskManifest as an invalid spec_model
    converter = ManifestToRegistrationConverter()
    with pytest.raises(TaskRegistryError):
        converter(manifest, entry_point_name="test_spec", entry_point_package="atomforge")

def test_converter_invalid_executor(manifest_factory):
    manifest = manifest_factory(executor_cls="nonexistent_plugin.code:Stuff")  # Using a nonexistent executor_class
    converter = ManifestToRegistrationConverter()
    registration, _ = converter(manifest, entry_point_name="test_executor", entry_point_package="atomforge")
    with pytest.raises((ImportError, ValueError, TypeError, AttributeError)):
        registration.load_executor_class()

def test_converter_invalid_result(manifest_factory):
    manifest = manifest_factory(result_model="atomforge.registry.task.manifest:TaskManifest")  # Using TaskManifest as an invalid result_model
    converter = ManifestToRegistrationConverter()
    registration, _ = converter(manifest, entry_point_name="test_result", entry_point_package="atomforge")
    with pytest.raises((TypeError, ValueError)):
        registration.load_result_model()

def test_converter_invalid_capability_spec(manifest_factory):
    manifest = manifest_factory(capability_spec="atomforge.registry.task.manifest:TaskManifest")  # Using TaskManifest as an invalid capability_spec
    converter = ManifestToRegistrationConverter()
    registration, _ = converter(manifest, entry_point_name="test_capability_spec", entry_point_package="atomforge")
    with pytest.raises((TypeError, ValueError)):
        registration.load_capability_spec()

def test_converter_wrapped_environment_factory(manifest_factory, example_structure):
    manifest = manifest_factory()
    converter = ManifestToRegistrationConverter()
    registration, _ = converter(manifest, entry_point_name="test_environment_factory", entry_point_package="atomforge")
    environment_factory = registration.load_environment_factory()
    example_task_spec = registration.spec_model(structure=example_structure)
    env_spec = environment_factory(example_task_spec)

    assert env_spec.provider_requirements == ("atomforge",)


def test_task_registration_validate_strict_warms_cache(manifest_factory):
    manifest = manifest_factory()
    converter = ManifestToRegistrationConverter()
    registration, _ = converter(
        manifest,
        entry_point_name="test_validate_strict",
        entry_point_package="atomforge",
    )

    registration.validate_strict()

    result_model = registration.load_result_model()
    registration.validate_strict()

    assert result_model is registration.load_result_model()
