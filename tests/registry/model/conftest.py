import pytest

from atomforge.registry.model.manifest import ModelManifest


@pytest.fixture
def manifest_factory():
    def factory(
        kind="ase-lj",
        model_spec="atomforge.model.ase_lj:LennardJones",
        executor_cls="atomforge.model.ase_lj:LennardJonesExecutor",
        supported_properties="atomforge.model.ase_lj:LennardJonesSupportedProperties",
        environment_factory_cls="atomforge.model.ase_lj:LennardJonesEnvironmentFactory",
        metadata="atomforge.model.ase_lj:LennardJonesMetadata",
        resource_capabilities="atomforge.model.ase_lj:LennardJonesResourceCapabilities",
        distribution=["atomforge"],
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
