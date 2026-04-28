import pytest

from atomforge_core.registry.model_manifest import ModelManifest


@pytest.fixture
def manifest_factory():
    def factory(
        kind="fake-model",
        model_spec="atomforge_core.model.spec:ModelSpec",
        executor_cls="atomforge_core.model.executor:ModelExecutor",
        supported_properties="atomforge_core.property:Property",
        environment_factory_cls="atomforge_core.env.factory:EnvironmentFactory",
        metadata="atomforge_core.model.metadata:ModelMetadata",
        resource_capabilities="atomforge_core.resources.resource_caps:ResourceCapabilities",
        distribution=["atomforge-core"],
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

    return factory

