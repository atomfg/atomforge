from atomforge_core.model.executor import ModelExecutor
from atomforge_core.model.result import ModelResult
from atomforge_core.property import Property
from atomforge_core.resources.resource_models import ResolvedResources
from atomforge_core.structure import StructureData

from atomforge_builtins.model.ase_lj.spec import LennardJones


class LennardJonesExecutor(ModelExecutor[LennardJones]):
    def __init__(
        self, spec: LennardJones, resolved_resources: ResolvedResources
    ) -> None:
        super().__init__(spec, resolved_resources)
        from ase.calculators.lj import LennardJones as ASELennardJones

        self._calc = ASELennardJones(
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

    def compute(
        self, structure: StructureData, properties: frozenset[Property]
    ) -> ModelResult:
        atoms = self.convert_structure(structure)
        atoms.calc = self._calc

        if Property.FORCES in properties:
            forces = atoms.get_forces()
        else:
            forces = None

        if Property.ENERGY in properties:
            energy = atoms.get_potential_energy()
        else:
            energy = None

        return ModelResult(
            energy=energy,
            forces=forces,
        )
