from atomforge.model import Model
from atomforge.env import EnvironmentSpec
from atomforge.structure import Structure
from atomforge.model.base import ModelResult

class CHGNet(Model):
    
    @property
    def model_name(self) -> str:
        return "CHGNet"

    def default_environment(self) -> EnvironmentSpec:
        return EnvironmentSpec(
            name=self.model_name, python="python3.12", requirements=["chgnet"]
        )
    
    @property
    def supported_properties(self):
        return frozenset({"energy", "forces"})
    
    def compute(self, structure: Structure, properties) -> ModelResult:
        from chgnet.model.dynamics import CHGNetCalculator

        calc = CHGNetCalculator()
        atoms = structure.to_ase()

        atoms.calc = calc

        if "forces" in properties:
            forces = atoms.get_forces()
        else:            
            forces = None

        if "energy" in properties:
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
    result = model.compute(structure, {"energy", "forces"})
    print(result)
