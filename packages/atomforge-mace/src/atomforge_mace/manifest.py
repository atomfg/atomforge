from atomforge.registry.model.manifest import ModelManifest

mace_manifest = ModelManifest(
    kind="mace",
    model_spec="atomforge_mace.mace_model:MACE",
    executor_cls="atomforge_mace.mace_model:MACEExecutor",
    supported_properties="atomforge_mace.mace_model:MACESupportedProperties",
    environment_factory_cls="atomforge_mace.mace_model:MACEEnvironmentFactory",
    metadata="atomforge_mace.mace_model:MACEMetadata",
    resource_capabilities="atomforge_mace.mace_model:MACEResourceCapabilities",
    distribution=["atomforge_mace"],
    probe="atomforge.model.probes:torch_probe",
)