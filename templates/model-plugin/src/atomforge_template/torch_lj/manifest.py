from atomforge_core.registry.model_manifest import ModelManifest

# The entry point in pyproject.toml targets this object. Components are referenced by
# "module:attr" strings, so registering the plugin imports nothing heavy.
torch_lj_manifest = ModelManifest(
    kind="torch-lj",
    model_spec="atomforge_template.torch_lj.spec:TorchLJ",
    executor_cls="atomforge_template.torch_lj.executor:TorchLJExecutor",
    supported_properties=(
        "atomforge_template.torch_lj.definitions:TorchLJSupportedProperties"
    ),
    environment_factory_cls=(
        "atomforge_template.torch_lj.environment:TorchLJEnvironmentFactory"
    ),
    metadata="atomforge_template.torch_lj.definitions:TorchLJMetadata",
    resource_capabilities=(
        "atomforge_template.torch_lj.definitions:TorchLJResourceCapabilities"
    ),
    # The distribution that provides this entry point. It is installed into the
    # worker environment alongside the requirements from the environment factory.
    distribution=["atomforge_template"],
    # Runs in the worker to report which accelerators are actually available.
    probe="atomforge_runtime.probes.torch_probe:torch_probe",
)
