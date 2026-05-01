from atomforge_core.model.executor import ModelExecutor
from atomforge_core.property import Property
from atomforge_core.structure import StructureData


class ModelCalculatorAdapter:
    implemented_properties = ["energy", "forces"]

    def __new__(cls, model_executor: ModelExecutor):
        from ase.calculators.calculator import Calculator

        class ASEModelCalculatorAdapter(Calculator):
            implemented_properties = cls.implemented_properties

            def __init__(self, executor: ModelExecutor):
                super().__init__()
                self.model_executor = executor

            def calculate(self, atoms, properties=None, system_changes=None):
                structure = convert_to_structure(atoms)
                model_result = self.model_executor.compute(
                    structure, {Property.ENERGY, Property.FORCES}
                )
                self.results["energy"] = model_result.energy
                self.results["forces"] = model_result.forces

        return ASEModelCalculatorAdapter(model_executor)


def convert_to_atoms(structure: StructureData):
    from ase import Atoms

    return Atoms(
        numbers=structure.numbers,
        positions=structure.positions,
        cell=structure.cell,
        pbc=structure.pbc,
    )


def convert_to_structure(atoms) -> StructureData:
    return StructureData(
        numbers=atoms.get_atomic_numbers().tolist(),
        positions=atoms.get_positions().tolist(),
        cell=atoms.get_cell().tolist(),
        pbc=atoms.get_pbc().tolist(),
    )
