from typing import Literal

from atomforge.env.base.env import EnvironmentSpec
from atomforge.model.core.executor import ModelExecutor
from atomforge.model.core.metadata import ModelMetadata, Reference
from atomforge.model.core.property import Property
from atomforge.model.core.resource_caps import ResourceCapabilities
from atomforge.model.core.result import ModelResult
from atomforge.model.core.spec import ModelSpec
from atomforge.structure import Structure
from atomforge.task.core.resources import ResolvedResources
from atomforge.env.base.factory import EnvironmentFactory, DependencySummary

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

    def compute(self, structure: Structure, properties: frozenset[Property]):
        atoms = structure.to_ase()
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
