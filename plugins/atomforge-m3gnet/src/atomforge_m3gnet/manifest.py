from atomforge_core.registry.model_manifest import ModelManifest

m3gnet_manifest = ModelManifest(
    kind="m3gnet",
    model_spec="atomforge_m3gnet.spec:M3GNet",
    executor_cls="atomforge_m3gnet.executor:M3GNetExecutor",
    environment_factory_cls="atomforge_m3gnet.environment:M3GNetEnvironmentFactory",
    supported_properties="atomforge_m3gnet.definitions:M3GNetSupportedProperties",
    resource_capabilities="atomforge_m3gnet.definitions:M3GNetResourceCapabilities",
    metadata="atomforge_m3gnet.definitions:M3GNetMetadata",
    distribution=["atomforge_m3gnet"],
)
