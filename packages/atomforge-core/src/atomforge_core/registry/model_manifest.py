from pydantic import Field

from atomforge_core.registry.base_manifest import RegistryManifestBase
from atomforge_core.registry.symbol_path import SymbolPath


class ModelManifest(RegistryManifestBase):
    kind: str = Field(description="Unique identifier for the model kind")
    model_spec: SymbolPath = Field(
        description="The model spec class, as a dotted path like 'my_package.my_module:MyModelSpec'"
    )
    executor_cls: SymbolPath = Field(
        description="The model executor class, as a dotted path like 'my_package.my_module:MyModelExecutor'"
    )
    supported_properties: SymbolPath = Field(
        description="The model supported properties object, as a dotted path like 'my_package.my_module:MySupportedProperties'"
    )
    environment_factory_cls: SymbolPath = Field(
        description="The environment factory class, as a dotted path like 'my_package.my_module:MyEnvironmentFactory'"
    )
    metadata: SymbolPath = Field(
        description="The model metadata object, as a dotted path like 'my_package.my_module:MyMetadata'"
    )
    resource_capabilities: SymbolPath = Field(
        description="The model resource capabilities object, as a dotted path like 'my_package.my_module:MyResourceCapabilities'"
    )
    distribution: list[str] | str = Field(
        default_factory=list,
        description="The distribution(s) that provide the model entry point.",
    )
    probe: SymbolPath | None = Field(
        default=None,
        description="Optional dotted path to a resource probe callable.",
    )
