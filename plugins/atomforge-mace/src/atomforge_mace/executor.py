from typing import Any

from atomforge_core.model.executor import ModelExecutor
from atomforge_core.model.result import ModelResult
from atomforge_core.property import Property
from atomforge_core.resources.resource_models import ResolvedResources
from atomforge_core.structure import StructureData

from atomforge_mace.spec import MACE


class MACEExecutor(ModelExecutor[MACE]):
    def __init__(self, spec: MACE, resolved_resources: ResolvedResources) -> None:
        super().__init__(spec, resolved_resources)
        from mace.calculators import mace_mp

        self._calc = mace_mp(
            model=spec.model,
            dispersion=spec.dispersion,
            **self.resource_conversion(resolved_resources),
        )

    def resource_conversion(
        self, resolved_resources: ResolvedResources
    ) -> dict[str, Any]:
        if resolved_resources.precision is not None:
            if resolved_resources.precision == "f64":
                default_dtype = "float64"
            elif resolved_resources.precision == "f32":
                default_dtype = "float32"
        else:
            default_dtype = "float32"

        if resolved_resources.accelerator == "gpu":
            device = "cuda"
        elif resolved_resources.accelerator == "mps":
            device = "mps"
        elif resolved_resources.accelerator == "cpu":
            device = "cpu"
        else:
            device = None

        return {"default_dtype": default_dtype, "device": device}

    def convert_structure(self, structure: StructureData):
        from ase import Atoms

        return Atoms(**structure.to_ase_dict())

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

        return ModelResult(energy=energy, forces=forces)
