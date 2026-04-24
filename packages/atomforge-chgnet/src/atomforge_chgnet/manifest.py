
from atomforge._core.registry.model_manifest import ModelManifest


chgnet_manifest = ModelManifest(
    kind="chgnet",
    model_spec="atomforge_chgnet.chgnet_model:CHGNet",
    executor_cls="atomforge_chgnet.chgnet_model:CHGNetExecutor",
    supported_properties="atomforge_chgnet.chgnet_model:CHGNetSupportedProperties",
    environment_factory_cls="atomforge_chgnet.chgnet_model:CHGNetEnvironmentFactory",
    metadata="atomforge_chgnet.chgnet_model:CHGNetMetadata",
    resource_capabilities="atomforge_chgnet.chgnet_model:CHGNetResourceCapabilities",
    distribution=["atomforge_chgnet"],
    probe="atomforge.model.probes:torch_probe",
)