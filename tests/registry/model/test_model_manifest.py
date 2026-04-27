import pytest

from atomforge_core.registry.model_manifest import ModelManifest


def test_model_manifest_factory_default(manifest_factory):
    manifest = manifest_factory()
    assert isinstance(manifest, ModelManifest)


def test_model_manifest_missing_distribution(manifest_factory):
    with pytest.raises(TypeError):
        manifest_factory(distribution=None)


def test_model_manifest_empty_distribution(manifest_factory):
    with pytest.raises(TypeError):
        manifest_factory(distribution=[])


def test_model_manifest_spec_improper_dotted_path(manifest_factory):
    with pytest.raises(Exception):
        manifest_factory(model_spec="not_a_dotted_path")


def test_model_manifest_executor_improper_dotted_path(manifest_factory):
    with pytest.raises(Exception):
        manifest_factory(executor_cls="not_a_dotted_path")


def test_model_manifest_supported_properties_improper_dotted_path(manifest_factory):
    with pytest.raises(Exception):
        manifest_factory(supported_properties="not_a_dotted_path")


def test_model_manifest_environment_factory_improper_dotted_path(manifest_factory):
    with pytest.raises(Exception):
        manifest_factory(environment_factory_cls="not_a_dotted_path")


def test_model_manifest_metadata_improper_dotted_path(manifest_factory):
    with pytest.raises(Exception):
        manifest_factory(metadata="not_a_dotted_path")


def test_model_manifest_resource_capabilities_improper_dotted_path(manifest_factory):
    with pytest.raises(Exception):
        manifest_factory(resource_capabilities="not_a_dotted_path")


def test_model_manifest_probe_improper_dotted_path(manifest_factory):
    with pytest.raises(Exception):
        manifest_factory(probe="not_a_dotted_path")
