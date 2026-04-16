from .registry import ModelRegistry
from .probes import torch_probe


def register_lennard_jones(registry: ModelRegistry):
    from .ase_lj import (
        LennardJonesExecutor,
        LennardJones,
        LennardJonesMetadata,
        lj_environment,
        LennardJonesSupportedProperties,
        model_kind,
        LennardJonesResourceCapabilities,
    )

    registry.register(
        model_kind=model_kind,
        model_spec=LennardJones,
        executor_class=LennardJonesExecutor,
        supported_properties=LennardJonesSupportedProperties,
        environment_factory=lj_environment,
        metadata=LennardJonesMetadata,
        resource_capabilities=LennardJonesResourceCapabilities,
        probe=None,
    )


def register_chgnet(registry: ModelRegistry):
    from .chgnet_model import (
        CHGNet,
        CHGNetExecutor,
        CHGNetMetadata,
        CHGNetSupportedProperties,
        chgnet_environment,
        CHGNetResourceCapabilities,
        model_kind,
    )

    registry.register(
        model_kind=model_kind,
        model_spec=CHGNet,
        executor_class=CHGNetExecutor,
        supported_properties=CHGNetSupportedProperties,
        environment_factory=chgnet_environment,
        metadata=CHGNetMetadata,
        resource_capabilities=CHGNetResourceCapabilities,
        probe=torch_probe,
    )


def register_mace(registry: ModelRegistry):
    from .mace_model import (
        MACE,
        MACEExecutor,
        MACEMetadata,
        MACESupportedProperties,
        mace_environment,
        MACEResourceCapabilities,
        model_kind,
    )

    registry.register(
        model_kind=model_kind,
        model_spec=MACE,
        executor_class=MACEExecutor,
        supported_properties=MACESupportedProperties,
        environment_factory=mace_environment,
        metadata=MACEMetadata,
        resource_capabilities=MACEResourceCapabilities,
        probe=torch_probe,
    )


def get_default_model_registry():
    registry = ModelRegistry()
    register_lennard_jones(registry)
    register_chgnet(registry)
    register_mace(registry)
    return registry
