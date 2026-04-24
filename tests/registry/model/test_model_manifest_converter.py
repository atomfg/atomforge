import pytest

from atomforge._builtins.model.ase_lj import LennardJones
from atomforge._runtime.registry.model.model_helpers import (
    ManifestToRegistrationConverter,
    ModelRegistryError,
)
from atomforge._runtime.registry.model.model_registration import ModelRegistration


def test_manifest_to_registration_converter(manifest_factory):
    manifest = manifest_factory()
    converter = ManifestToRegistrationConverter()
    registration, kind = converter(
        manifest, entry_point_name="test_registration", entry_point_package="atomforge"
    )

    assert isinstance(registration, ModelRegistration)
    assert kind == "ase-lj"


def test_converter_invalid_model_spec(manifest_factory):
    manifest = manifest_factory(
        model_spec="atomforge.registry.model.manifest:ModelManifest"
    )
    converter = ManifestToRegistrationConverter()
    with pytest.raises(ModelRegistryError):
        converter(manifest, entry_point_name="test_spec", entry_point_package="atomforge")


def test_converter_invalid_executor(manifest_factory):
    manifest = manifest_factory(
        executor_cls="atomforge.registry.model.manifest:ModelManifest"
    )
    converter = ManifestToRegistrationConverter()
    with pytest.raises(ModelRegistryError):
        converter(
            manifest, entry_point_name="test_executor", entry_point_package="atomforge"
        )


def test_converter_invalid_supported_properties(manifest_factory):
    manifest = manifest_factory(
        supported_properties="atomforge.registry.model.manifest:ModelManifest"
    )
    converter = ManifestToRegistrationConverter()
    with pytest.raises(ModelRegistryError):
        converter(
            manifest,
            entry_point_name="test_supported_properties",
            entry_point_package="atomforge",
        )


def test_converter_invalid_metadata(manifest_factory):
    manifest = manifest_factory(metadata="atomforge.registry.model.manifest:ModelManifest")
    converter = ManifestToRegistrationConverter()
    with pytest.raises(ModelRegistryError):
        converter(
            manifest, entry_point_name="test_metadata", entry_point_package="atomforge"
        )


def test_converter_invalid_resource_capabilities(manifest_factory):
    manifest = manifest_factory(
        resource_capabilities="atomforge.registry.model.manifest:ModelManifest"
    )
    converter = ManifestToRegistrationConverter()
    with pytest.raises(ModelRegistryError):
        converter(
            manifest,
            entry_point_name="test_resource_capabilities",
            entry_point_package="atomforge",
        )


def test_converter_invalid_probe(manifest_factory):
    manifest = manifest_factory(probe="atomforge.registry.model.manifest:ModelManifest")
    converter = ManifestToRegistrationConverter()
    with pytest.raises(ModelRegistryError):
        converter(manifest, entry_point_name="test_probe", entry_point_package="atomforge")


def test_converter_rejects_mismatched_distribution(manifest_factory):
    manifest = manifest_factory(distribution=["third-party-plugin"])
    converter = ManifestToRegistrationConverter()
    with pytest.raises(ModelRegistryError):
        converter(
            manifest,
            entry_point_name="test_distribution",
            entry_point_package="atomforge",
        )


def test_converter_wrapped_environment_factory(manifest_factory):
    manifest = manifest_factory()
    converter = ManifestToRegistrationConverter()
    registration, _ = converter(
        manifest,
        entry_point_name="test_environment_factory",
        entry_point_package="atomforge",
    )
    environment_factory = registration.environment_factory
    example_model_spec = LennardJones()
    env_spec = environment_factory(example_model_spec)

    assert env_spec.provider_requirements == (
        ManifestToRegistrationConverter._resolve_distribution("atomforge"),
    )


def test_converter_loads_optional_probe(manifest_factory):
    manifest = manifest_factory(probe="atomforge._runtime.probes.torch_probe:torch_probe")
    converter = ManifestToRegistrationConverter()
    registration, _ = converter(
        manifest,
        entry_point_name="test_optional_probe",
        entry_point_package="atomforge",
    )

    assert callable(registration.probe)
