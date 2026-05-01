from atomforge_core.registry.model_manifest import ModelManifest

lennard_jones_manifest = ModelManifest(
    kind="ase-lj",
    model_spec="atomforge_builtins.model.ase_lj.spec:LennardJones",
    executor_cls="atomforge_builtins.model.ase_lj.executor:LennardJonesExecutor",
    supported_properties="atomforge_builtins.model.ase_lj.definitions:LennardJonesSupportedProperties",
    environment_factory_cls="atomforge_builtins.model.ase_lj.environment:LennardJonesEnvironmentFactory",
    metadata="atomforge_builtins.model.ase_lj.definitions:LennardJonesMetadata",
    resource_capabilities="atomforge_builtins.model.ase_lj.definitions:LennardJonesResourceCapabilities",
    distribution=["atomforge_builtins"],
)
