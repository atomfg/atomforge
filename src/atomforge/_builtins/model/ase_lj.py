from typing import Literal

from atomforge._core.env.env import EnvironmentSpec
from atomforge._core.model.executor import ModelExecutor
from atomforge._core.model.metadata import ModelMetadata, Reference
from atomforge._core.property import Property
from atomforge._core.resources.resource_caps import ResourceCapabilities
from atomforge._core.model.result import ModelResult
from atomforge._core.model.spec import ModelSpec
from atomforge._core.structure import StructureData
from atomforge._core.resources.resource_models import ResolvedResources
from atomforge._core.env.factory import EnvironmentFactory, DependencySummary

description = """Lennard-Jones potential implemented in the Atomic Simulation Environment (ASE).
"""

model_kind = "ase-lj"
LennardJonesSupportedProperties = frozenset({Property.ENERGY, Property.FORCES})


class LennardJones(ModelSpec):
    kind: Literal["ase-lj"] = model_kind
    sigma: float = 1.0
    epsilon: float = 1.0
    rc: float | None = None
    ro: float | None = None
    smooth: bool = False


LennardJonesMetadata = ModelMetadata(
    id=model_kind,
    name="ASE Lennard-Jones",
    method_family="empirical",
    references=(
        Reference(label="ASE Documentation", url="https://ase-lib.org/", kind="docs"),
    ),
    description=description,
)


LennardJonesResourceCapabilities = ResourceCapabilities(
    accelerator=["cpu"], precision=None
)


class LennardJonesEnvironmentFactory(EnvironmentFactory[LennardJones]):
    dependency_summary = DependencySummary(
        base_requirements=("ase",),
        python="python3.12",
    )

    def build(self, spec: LennardJones) -> EnvironmentSpec:
        return EnvironmentSpec(
            name=spec.kind, python="python3.12", requirements=["ase"]
        )


class LennardJonesExecutor(ModelExecutor[LennardJones]):
    def __init__(
        self, spec: LennardJones, resolved_resources: ResolvedResources
    ) -> None:
        super().__init__(spec, resolved_resources)
        from ase.calculators.lj import LennardJones

        self._calc = LennardJones(
            sigma=spec.sigma,
            epsilon=spec.epsilon,
            rc=spec.rc,
            ro=spec.ro,
            smooth=spec.smooth,
        )

    def convert_structure(self, structure: StructureData):
        from ase import Atoms

        return Atoms(
            positions=structure.positions,
            cell=structure.cell,
            numbers=structure.numbers,
            pbc=structure.pbc,
        )

    def compute(self, structure: StructureData, properties: frozenset[Property]):
        atoms = self.convert_structure(structure)
        atoms.calc = self._calc

        # Calculate forces if requested, otherwise set to None to avoid unnecessary computation
        if Property.FORCES in properties:
            forces = atoms.get_forces()
        else:
            forces = None

        # Calculate energy if requested, otherwise set to None to avoid unnecessary computation
        # If forces were requested ASE will have already calculated the energy, so this won't trigger an additional calculation
        if Property.ENERGY in properties:
            energy = atoms.get_potential_energy()
        else:
            energy = None

        return ModelResult(
            energy=energy,
            forces=forces,
        )
