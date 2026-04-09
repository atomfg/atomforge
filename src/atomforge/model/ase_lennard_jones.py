from atomforge.model import Model
from atomforge.env import EnvironmentSpec
from atomforge.structure import Structure

class ASELennardJones(Model):
    
    @property
    def model_name(self) -> str:
        return "ase_lennard_jones"

    def default_environment(self) -> EnvironmentSpec:
        return EnvironmentSpec(
            name=self.model_name, python="python3.12", requirements=["ase"]
        )
    
    @property
    def supported_properties(self):
        return frozenset({"energy", "forces"})
    
    def compute(self, structure: Structure, properties):
        from ase.calculators.lj import LennardJones

        calc = LennardJones()
        atoms = structure.to_ase()
        atoms.set_calculator(calc)
        energy = atoms.get_potential_energy() if "energy" in properties else None
        forces = atoms.get_forces() if "forces" in properties else None
        return {"energy": energy, "forces": forces}
    
