from atomforge_core.registry.model_manifest import ModelManifest

manifest = ModelManifest(
    kind="mg3net",
    model_spec="atomforge_mg3net.model:MG3Net",
    executor_cls="atomforge_mg3net.model:MG3NetExecutor",
    environment_factory_cls="atomforge_mg3net.model:MG3NetEnvironmentFactory",
    supported_properties="atomforge_mg3net.model:MG3NetSupportedProperties",
    resource_capabilities="atomforge_mg3net.model:MG3NetResourceCapabilities",
    metadata="atomforge_mg3net.model:MG3NetMetadata",
    distribution="atomforge-mg3net",
)
