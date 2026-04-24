from typing import Literal

from atomforge.env.base.env import EnvironmentSpec
from atomforge.model.core.executor import ModelExecutor
from atomforge.model.core.metadata import ModelMetadata
from atomforge.model.core.property import Property
from atomforge.model.core.resource_caps import ResourceCapabilities
from atomforge.model.core.result import ModelResult
from atomforge.model.core.spec import ModelSpec
from atomforge.structure import StructureData
from atomforge.task.core.resources import ResolvedResources
from atomforge.env.base.factory import EnvironmentFactory, DependencySummary

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
        base_requirements=("ase",),
        python="python3.12",
    )

    def build(self, spec: NoDep) -> EnvironmentSpec:
        return EnvironmentSpec(
            name=spec.kind, python="python3.12", requirements=["ase"]
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
