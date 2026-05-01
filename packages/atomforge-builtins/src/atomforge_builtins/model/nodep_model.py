from typing import Literal

from atomforge_core.env.env import EnvironmentSpec
from atomforge_core.model.executor import ModelExecutor
from atomforge_core.model.metadata import ModelMetadata
from atomforge_core.property import Property
from atomforge_core.registry.model_manifest import ModelManifest
from atomforge_core.resources.resource_caps import ResourceCapabilities
from atomforge_core.model.result import ModelResult
from atomforge_core.model.spec import ModelSpec
from atomforge_core.structure import StructureData
from atomforge_core.resources.resource_models import ResolvedResources
from atomforge_core.env.factory import EnvironmentFactory, DependencySummary

description = """A model with no dependencies, used for testing purposes."""

model_kind = "no-dep"
NoDepSupportedProperties = frozenset({Property.ENERGY, Property.FORCES})


class NoDep(ModelSpec):
    kind: Literal["no-dep"] = model_kind
    scale: float = 1.0


NoDepMetadata = ModelMetadata(
    id=model_kind,
    name="No Dependency Model",
    method_family="empirical",
    description=description,
)


NoDepCapabilities = ResourceCapabilities(
    accelerator=["cpu"], precision=None
)


class NoDepEnvironmentFactory(EnvironmentFactory[NoDep]):
    dependency_summary = DependencySummary(
        base_requirements=(),
        python="3.12",
    )

    def build(self, spec: NoDep) -> EnvironmentSpec:
        return EnvironmentSpec(
            name=spec.kind, python="3.12", requirements=[]
        )


class NoDepExecutor(ModelExecutor[NoDep]):
    def __init__(
        self, spec: NoDep, resolved_resources: ResolvedResources
    ) -> None:
        super().__init__(spec, resolved_resources)

    def compute(self, structure: StructureData, properties: frozenset[Property]):

        # Calculate forces if requested, otherwise set to None to avoid unnecessary computation
        if Property.FORCES in properties:
            forces = [[0.0, 0.0, 0.0] for _ in structure.numbers]
        else:
            forces = None

        # Calculate energy if requested, otherwise set to None to avoid unnecessary computation
        # If forces were requested ASE will have already calculated the energy, so this won't trigger an additional calculation
        if Property.ENERGY in properties:
            energy = len(structure.numbers) * -0.1 * self.spec.scale  # Dummy energy calculation based on number of atoms
        else:
            energy = None

        return ModelResult(
            energy=energy,
            forces=forces,
        )


no_dep_manifest = ModelManifest(
    kind="no-dep",
    model_spec="atomforge_builtins.model.nodep_model:NoDep",
    executor_cls="atomforge_builtins.model.nodep_model:NoDepExecutor",
    supported_properties="atomforge_builtins.model.nodep_model:NoDepSupportedProperties",
    environment_factory_cls="atomforge_builtins.model.nodep_model:NoDepEnvironmentFactory",
    metadata="atomforge_builtins.model.nodep_model:NoDepMetadata",
    resource_capabilities="atomforge_builtins.model.nodep_model:NoDepCapabilities",
    distribution=["atomforge_builtins"],
)
