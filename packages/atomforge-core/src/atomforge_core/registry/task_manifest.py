from pydantic import Field

from atomforge_core.registry.base_manifest import RegistryManifestBase
from atomforge_core.registry.symbol_path import SymbolPath


class TaskManifest(RegistryManifestBase):
    kind: str = Field(description="Unique identifier for the task kind")
    spec_model: SymbolPath = Field(
        description="The specification model for the task, as a dotted path to a class, e.g. 'my_package.my_module:MySpecModel'"
    )
    executor_cls: SymbolPath | None = Field(
        description="The executor class for the task, as a dotted path to a class, e.g. 'my_package.my_module:MyTaskExecutor'. If not provided, the task will require model overrides to specify the executor."
    )
    result_model: SymbolPath = Field(
        description="The result model for the task, as a dotted path to a class, e.g. 'my_package.my_module:MyResultModel'"
    )
    capability_spec: SymbolPath = Field(
        description="The capability specification for the task, as a dotted path to a class, e.g. 'my_package.my_module:MyCapabilitySpec'"
    )
    environment_factory_cls: SymbolPath = Field(
        description="The environment factory class for the task, as a dotted path to a class, e.g. 'my_package.my_module:MyEnvironmentFactory'"
    )
