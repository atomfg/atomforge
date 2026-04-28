import pytest

from atomforge_core.registry.model_manifest import ModelManifest
from atomforge_core.registry.symbol_path import SymbolPath
from atomforge_runtime.registry.model.model_helpers import (
    ManifestToRegistrationConverter,
    ModelRegistryError,
)
from atomforge_runtime.registry.model.model_registration import ModelRegistration

from runtime_fakes import FakeModel


def manifest_factory(
    kind="fake-model",
    model_spec="runtime_fakes:FakeModel",
    executor_cls="runtime_fakes:FakeModelExecutor",
    supported_properties="runtime_fakes:FakeSupportedProperties",
    environment_factory_cls="runtime_fakes:FakeEnvironmentFactory",
    metadata="runtime_fakes:FakeMetadata",
    resource_capabilities="runtime_fakes:FakeResourceCapabilities",
    distribution=["runtime-test-plugin"],
    probe=None,
):
    return ModelManifest(
        kind=kind,
        model_spec=model_spec,
        executor_cls=executor_cls,
        supported_properties=supported_properties,
        environment_factory_cls=environment_factory_cls,
        metadata=metadata,
        resource_capabilities=resource_capabilities,
        distribution=distribution,
        probe=probe,
    )


def test_manifest_to_registration_converter():
    manifest = manifest_factory()
    converter = ManifestToRegistrationConverter()
    registration, kind = converter(
        manifest,
        entry_point_name="test_registration",
        entry_point_package="runtime-test-plugin",
    )

    assert isinstance(registration, ModelRegistration)
    assert kind == "fake-model"


def test_converter_invalid_model_spec():
    manifest = manifest_factory(model_spec="runtime_fakes:FakeMetadata")
    converter = ManifestToRegistrationConverter()
    with pytest.raises(ModelRegistryError):
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
    with pytest.raises((TypeError, ValueError)):
        registration.load_executor_class()


def test_converter_invalid_supported_properties():
    manifest = manifest_factory(supported_properties="runtime_fakes:FakeMetadata")
    converter = ManifestToRegistrationConverter()
    registration, _ = converter(
        manifest,
        entry_point_name="test_supported_properties",
        entry_point_package="runtime-test-plugin",
    )
    with pytest.raises((TypeError, ValueError)):
        registration.load_supported_properties()


def test_converter_invalid_metadata():
    manifest = manifest_factory(metadata="runtime_fakes:FakeModel")
    converter = ManifestToRegistrationConverter()
    registration, _ = converter(
        manifest,
        entry_point_name="test_metadata",
        entry_point_package="runtime-test-plugin",
    )
    with pytest.raises((TypeError, ValueError)):
        registration.load_metadata()


def test_converter_invalid_resource_capabilities():
    manifest = manifest_factory(resource_capabilities="runtime_fakes:FakeMetadata")
    converter = ManifestToRegistrationConverter()
    registration, _ = converter(
        manifest,
        entry_point_name="test_resource_capabilities",
        entry_point_package="runtime-test-plugin",
    )
    with pytest.raises((TypeError, ValueError)):
        registration.load_resource_capabilities()


def test_converter_invalid_probe():
    manifest = manifest_factory(probe="runtime_fakes:FakeMetadata")
    converter = ManifestToRegistrationConverter()
    registration, _ = converter(
        manifest,
        entry_point_name="test_probe",
        entry_point_package="runtime-test-plugin",
    )
    with pytest.raises((TypeError, ValueError)):
        registration.load_probe()


def test_converter_rejects_mismatched_distribution():
    manifest = manifest_factory(distribution=["third-party-plugin"])
    converter = ManifestToRegistrationConverter()
    with pytest.raises(ModelRegistryError):
        converter(
            manifest,
            entry_point_name="test_distribution",
            entry_point_package="runtime-test-plugin",
        )


def test_converter_wrapped_environment_factory():
    manifest = manifest_factory()
    converter = ManifestToRegistrationConverter()
    registration, _ = converter(
        manifest,
        entry_point_name="test_environment_factory",
        entry_point_package="runtime-test-plugin",
    )
    environment_factory = registration.load_environment_factory()
    env_spec = environment_factory(FakeModel())

    assert env_spec.provider_requirements == ("runtime-test-plugin",)


def test_converter_loads_optional_probe():
    manifest = manifest_factory(probe="runtime_fakes:fake_probe")
    converter = ManifestToRegistrationConverter()
    registration, _ = converter(
        manifest,
        entry_point_name="test_optional_probe",
        entry_point_package="runtime-test-plugin",
    )

    assert callable(registration.load_probe())


def test_model_registration_validate_strict_warms_cache_and_allows_optional_probe():
    manifest = manifest_factory(probe=None)
    converter = ManifestToRegistrationConverter()
    registration, _ = converter(
        manifest,
        entry_point_name="test_validate_strict",
        entry_point_package="runtime-test-plugin",
    )

    registration.validate_strict()

    metadata = registration.load_metadata()
    registration.validate_strict()

    assert metadata is registration.load_metadata()
    assert registration.load_probe() is None


def test_converter_leaves_lazy_fields_as_symbol_paths():
    manifest = manifest_factory()
    converter = ManifestToRegistrationConverter()
    registration, _ = converter(
        manifest,
        entry_point_name="test_lazy_paths",
        entry_point_package="runtime-test-plugin",
    )

    assert registration.metadata_path == SymbolPath(manifest.metadata.raw)
    assert registration.supported_properties_path == SymbolPath(
        manifest.supported_properties.raw
    )

