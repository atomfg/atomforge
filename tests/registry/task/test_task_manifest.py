import pytest
from atomforge._core.registry.task_manifest import TaskManifest


def test_task_manifest_factory_default(manifest_factory):
    manifest = manifest_factory()
    assert isinstance(manifest, TaskManifest)


def test_task_manifest_missing_distribution(manifest_factory):
    with pytest.raises(TypeError):
        manifest_factory(distribution=None)


def test_task_manifest_empty_distribution(manifest_factory):
    with pytest.raises(TypeError):
        manifest_factory(distribution=[])


def test_task_manifest_spec_improper_dotted_path(manifest_factory):
    with pytest.raises(TypeError):
        manifest_factory(spec_model="not_a_dotted_path")


def test_task_manifest_executor_improper_dotted_path(manifest_factory):
    with pytest.raises(TypeError):
        manifest_factory(executor_cls="not_a_dotted_path")


def test_task_manifest_result_improper_dotted_path(manifest_factory):
    with pytest.raises(TypeError):
        manifest_factory(result_model="not_a_dotted_path")


def test_task_manifest_capability_spec_improper_dotted_path(manifest_factory):
    with pytest.raises(TypeError):
        manifest_factory(capability_spec="not_a_dotted_path")


def test_task_manifest_environment_factory_improper_dotted_path(manifest_factory):
    with pytest.raises(TypeError):
        manifest_factory(environment_factory_cls="not_a_dotted_path")
