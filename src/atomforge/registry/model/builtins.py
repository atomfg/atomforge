from atomforge.registry.model.manifest import ModelManifest


lennard_jones_manifest = ModelManifest(
    kind="ase-lj",
    model_spec="atomforge.model.ase_lj:LennardJones",
    executor_cls="atomforge.model.ase_lj:LennardJonesExecutor",
    supported_properties="atomforge.model.ase_lj:LennardJonesSupportedProperties",
    environment_factory_cls="atomforge.model.ase_lj:LennardJonesEnvironmentFactory",
    metadata="atomforge.model.ase_lj:LennardJonesMetadata",
    resource_capabilities="atomforge.model.ase_lj:LennardJonesResourceCapabilities",
    distribution=["atomforge"],
)
