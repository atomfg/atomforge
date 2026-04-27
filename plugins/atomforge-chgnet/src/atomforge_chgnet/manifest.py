from atomforge_core.registry.model_manifest import ModelManifest

chgnet_manifest = ModelManifest(
    kind="chgnet",
    model_spec="atomforge_chgnet.spec:CHGNet",
    executor_cls="atomforge_chgnet.executor:CHGNetExecutor",
    supported_properties="atomforge_chgnet.definitions:CHGNetSupportedProperties",
    environment_factory_cls="atomforge_chgnet.environment:CHGNetEnvironmentFactory",
    metadata="atomforge_chgnet.definitions:CHGNetMetadata",
    resource_capabilities="atomforge_chgnet.definitions:CHGNetResourceCapabilities",
    distribution=["atomforge_chgnet"],
    probe="atomforge_runtime.probes.torch_probe:torch_probe",
)
