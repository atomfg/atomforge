import pytest
from atomforge.registry.task.helpers import ManifestToRegistrationConverter, TaskRegistryError
from atomforge.registry.task.registration import TaskRegistration

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
    manifest = manifest_factory(executor_cls="atomforge.registry.task.manifest:TaskManifest")  # Using TaskManifest as an invalid executor_class
    converter = ManifestToRegistrationConverter()
    with pytest.raises(TaskRegistryError):
        converter(manifest, entry_point_name="test_executor", entry_point_package="atomforge")

def test_converter_invalid_result(manifest_factory):
    manifest = manifest_factory(result_model="atomforge.registry.task.manifest:TaskManifest")  # Using TaskManifest as an invalid result_model
    converter = ManifestToRegistrationConverter()
    with pytest.raises(TaskRegistryError):
        converter(manifest, entry_point_name="test_result", entry_point_package="atomforge")

def test_converter_invalid_capability_spec(manifest_factory):
    manifest = manifest_factory(capability_spec="atomforge.registry.task.manifest:TaskManifest")  # Using TaskManifest as an invalid capability_spec
    converter = ManifestToRegistrationConverter()
    with pytest.raises(TaskRegistryError):
        converter(manifest, entry_point_name="test_capability_spec", entry_point_package="atomforge")

def test_converter_wrapped_environment_factory(manifest_factory, example_structure):
    manifest = manifest_factory()
    converter = ManifestToRegistrationConverter()
    registration, _ = converter(manifest, entry_point_name="test_environment_factory", entry_point_package="atomforge")
    environment_factory = registration.environment_factory
    example_task_spec = registration.spec_model(structure=example_structure)
    env_spec = environment_factory(example_task_spec)

    assert env_spec.provider_requirements == (ManifestToRegistrationConverter._resolve_distribution("atomforge"),)


