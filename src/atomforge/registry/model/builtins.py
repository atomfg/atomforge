from atomforge.registry.model.manifest import ModelManifest


lennard_jones_manifest = ModelManifest(
    kind="ase-lj",
    model_spec="atomforge.model.ase_lj:LennardJones",
    executor_class="atomforge.model.ase_lj:LennardJonesExecutor",
    supported_properties="atomforge.model.ase_lj:LennardJonesSupportedProperties",
    environment_factory="atomforge.model.ase_lj:lj_environment",
    metadata="atomforge.model.ase_lj:LennardJonesMetadata",
    resource_capabilities="atomforge.model.ase_lj:LennardJonesResourceCapabilities",
    distribution=["atomforge"],
)

chgnet_manifest = ModelManifest(
    kind="chgnet",
    model_spec="atomforge.model.chgnet_model:CHGNet",
    executor_class="atomforge.model.chgnet_model:CHGNetExecutor",
    supported_properties="atomforge.model.chgnet_model:CHGNetSupportedProperties",
    environment_factory="atomforge.model.chgnet_model:chgnet_environment",
    metadata="atomforge.model.chgnet_model:CHGNetMetadata",
    resource_capabilities="atomforge.model.chgnet_model:CHGNetResourceCapabilities",
    distribution=["atomforge"],
    probe="atomforge.model.probes:torch_probe",
)

mace_manifest = ModelManifest(
    kind="mace",
    model_spec="atomforge.model.mace_model:MACE",
    executor_class="atomforge.model.mace_model:MACEExecutor",
    supported_properties="atomforge.model.mace_model:MACESupportedProperties",
    environment_factory="atomforge.model.mace_model:mace_environment",
    metadata="atomforge.model.mace_model:MACEMetadata",
    resource_capabilities="atomforge.model.mace_model:MACEResourceCapabilities",
    distribution=["atomforge"],
    probe="atomforge.model.probes:torch_probe",
)
