from atomforge_core.registry.model_manifest import ModelManifest

mace_manifest = ModelManifest(
    kind="mace",
    model_spec="atomforge_mace.spec:MACE",
    executor_cls="atomforge_mace.executor:MACEExecutor",
    supported_properties="atomforge_mace.definitions:MACESupportedProperties",
    environment_factory_cls="atomforge_mace.environment:MACEEnvironmentFactory",
    metadata="atomforge_mace.definitions:MACEMetadata",
    resource_capabilities="atomforge_mace.definitions:MACEResourceCapabilities",
    distribution=["atomforge_mace"],
    probe="atomforge_runtime.probes.torch_probe:torch_probe",
)
