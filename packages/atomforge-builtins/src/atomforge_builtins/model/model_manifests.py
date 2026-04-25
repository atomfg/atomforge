from atomforge_core.registry.model_manifest import ModelManifest


lennard_jones_manifest = ModelManifest(
    kind="ase-lj",
    model_spec="atomforge_builtins.model.ase_lj:LennardJones",
    executor_cls="atomforge_builtins.model.ase_lj:LennardJonesExecutor",
    supported_properties="atomforge_builtins.model.ase_lj:LennardJonesSupportedProperties",
    environment_factory_cls="atomforge_builtins.model.ase_lj:LennardJonesEnvironmentFactory",
    metadata="atomforge_builtins.model.ase_lj:LennardJonesMetadata",
    resource_capabilities="atomforge_builtins.model.ase_lj:LennardJonesResourceCapabilities",
    distribution=["atomforge_builtins"],
)

no_dep_manifest = ModelManifest(
    kind="no-dep",
    model_spec="atomforge_builtins.model.nodep_model:NoDep",
    executor_cls="atomforge_builtins.model.nodep_model:NoDepExecutor",
    supported_properties="atomforge_builtins.model.nodep_model:NoDepSupportedProperties",
    environment_factory_cls="atomforge_builtins.model.nodep_model:NoDepEnvironmentFactory",
    metadata="atomforge_builtins.model.nodep_model:NoDepMetadata",
    resource_capabilities="atomforge_builtins.model.nodep_model:NoDepCapabilities",
    distribution=["atomforge_builtins"],
)