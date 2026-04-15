from atomforge.model.base import Model
from atomforge.env import EnvironmentSpec
from atomforge.structure import Structure
from atomforge.model.base import ModelResult, Property, ModelMetadata, Reference


class ASELennardJones(Model):
    model_kind: str = "ase_lennard_jones"
    supported_properties: frozenset[Property] = frozenset(
        {Property.ENERGY, Property.FORCES}
    )
    metadata: ModelMetadata = ModelMetadata(
        id="ase_lennard_jones",
        name="ASE Lennard-Jones",
        method_family="empirical",
        references=(
            Reference(
                label="ASE Documentation", url="https://ase-lib.org/", kind="docs"
            ),
        ),
    )

    def default_environment(self) -> EnvironmentSpec:
        return EnvironmentSpec(
            name=self.model_kind, python="python3.12", requirements=["ase"]
        )

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
