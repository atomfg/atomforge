import pytest

from atomforge.registry.model.manifest import ModelManifest


@pytest.fixture
def manifest_factory():
    def factory(
        kind="ase-lj",
        model_spec="atomforge.model.ase_lj:LennardJones",
        executor_class="atomforge.model.ase_lj:LennardJonesExecutor",
        supported_properties="atomforge.model.ase_lj:LennardJonesSupportedProperties",
        environment_factory="atomforge.model.ase_lj:lj_environment",
        metadata="atomforge.model.ase_lj:LennardJonesMetadata",
        resource_capabilities="atomforge.model.ase_lj:LennardJonesResourceCapabilities",
        distribution=["atomforge"],
        probe=None,
    ):
        return ModelManifest(
            kind=kind,
            model_spec=model_spec,
            executor_class=executor_class,
            supported_properties=supported_properties,
            environment_factory=environment_factory,
            metadata=metadata,
            resource_capabilities=resource_capabilities,
            distribution=distribution,
            probe=probe,
        )

    return factory
