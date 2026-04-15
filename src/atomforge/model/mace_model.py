from atomforge.model import Model
from atomforge.env import EnvironmentSpec
from atomforge.structure import Structure
from atomforge.model.base import ModelResult, Property, ModelMetadata, Reference


class MACE(Model):
    model_kind: str = "mace"
    supported_properties: frozenset[Property] = frozenset(
        {Property.ENERGY, Property.FORCES}
    )
    metadata: ModelMetadata = ModelMetadata(
        id="mace",
        name="MACE",
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
            name=self.model_kind, python="python3.12", requirements=["mace-torch", "torch"]
        )
    
    def instantiate_model(self):
        from mace.calculators import mace_mp
        calc = mace_mp(model="medium", dispersion=False, default_dtype="float32")
        return calc


    def compute(self, structure: Structure, properties) -> ModelResult:
        calc = self.instantiate_model()
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
