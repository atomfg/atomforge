from atomforge_core.registry.model_manifest import ModelManifest

# The entry point in pyproject.toml targets this object. Components are referenced by
# "module:attr" strings, so registering the plugin imports nothing heavy.
torch_lj_manifest = ModelManifest(
    kind="torch-lj",
    model_spec="atomforge_template.spec:TorchLJ",
    executor_cls="atomforge_template.executor:TorchLJExecutor",
    supported_properties="atomforge_template.definitions:TorchLJSupportedProperties",
    environment_factory_cls="atomforge_template.environment:TorchLJEnvironmentFactory",
    metadata="atomforge_template.definitions:TorchLJMetadata",
    resource_capabilities="atomforge_template.definitions:TorchLJResourceCapabilities",
    # The distribution that provides this entry point. It is installed into the
    # worker environment alongside the requirements from the environment factory.
    distribution=["atomforge_template"],
    # Runs in the worker to report which accelerators are actually available.
    probe="atomforge_runtime.probes.torch_probe:torch_probe",
    # Optional: the declared facts about each variant.
    variant_info="atomforge_template.definitions:torch_lj_variant_info",
)
