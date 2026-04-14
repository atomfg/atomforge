from atomforge.model.base import Model
from atomforge.env import EnvironmentSpec
from atomforge.structure import Structure
from atomforge.model.base import ModelResult, Property


class ASELennardJones(Model):
    @property
    def model_kind(self) -> str:
        return "ase_lennard_jones"

    def default_environment(self) -> EnvironmentSpec:
        return EnvironmentSpec(
            name=self.model_kind, python="python3.12", requirements=["ase"]
        )

    @property
    def supported_properties(self):
        return frozenset({Property.ENERGY, Property.FORCES})

    def compute(self, structure: Structure, properties) -> ModelResult:
        from ase.calculators.lj import LennardJones

        calc = LennardJones(sigma=1, epsilon=1)
        atoms = structure.to_ase()

        atoms.calc = calc

        if Property.FORCES in properties:
            forces = atoms.get_forces()
        else:
            forces = None

        if Property.ENERGY in properties:
            energy = atoms.get_potential_energy()
        else:
            energy = None

        return ModelResult(energy=energy, forces=forces)


if __name__ == "__main__":
    from atomforge.structure import Structure
    from ase.build import molecule
    from rich import print

    model = ASELennardJones()
    structure = Structure.from_ase(molecule("H2O"))
    result = model.compute(structure, {Property.ENERGY, Property.FORCES})
    print(result)
