from atomforge.model import Model
from atomforge.env import EnvironmentSpec
from atomforge.structure import Structure
from atomforge.model.base import ModelResult, Property, ModelMetadata, Reference


class CHGNet(Model):
    model_kind: str = "chgnet"
    supported_properties: frozenset[Property] = frozenset(
        {Property.ENERGY, Property.FORCES}
    )
    metadata: ModelMetadata = ModelMetadata(
        id="chgnet",
        name="CHGNet",
        method_family="mlip",
        references=(
            Reference(
                label="GitHub Repository",
                url="https://github.com/CederGroupHub/chgnet",
                kind="repo",
            ),
            Reference(
                label="Paper",
                url="https://www.nature.com/articles/s42256-023-00716-3",
                kind="paper",
            ),
        ),
    )

    def default_environment(self) -> EnvironmentSpec:
        return EnvironmentSpec(
            name=self.model_kind, python="python3.12", requirements=["chgnet"]
        )

    def compute(self, structure: Structure, properties) -> ModelResult:
        from chgnet.model.dynamics import CHGNetCalculator

        calc = CHGNetCalculator()
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

    model = CHGNet()
    atoms = molecule("H2O")
    atoms.cell = [10, 10, 10]
    structure = Structure.from_ase(atoms)
    result = model.compute(structure, {Property.ENERGY, Property.FORCES})
    print(result)
