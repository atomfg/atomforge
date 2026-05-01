from atomforge_core.model.executor import ModelExecutor
from atomforge_core.model.result import ModelResult
from atomforge_core.property import Property
from atomforge_core.resources.resource_models import ResolvedResources
from atomforge_core.structure import StructureData

from atomforge_chgnet.spec import CHGNet


class CHGNetExecutor(ModelExecutor[CHGNet]):
    def __init__(self, spec: CHGNet, resolved_resources: ResolvedResources) -> None:
        super().__init__(spec, resolved_resources)
        from chgnet.model.dynamics import CHGNetCalculator
        from chgnet.model import CHGNet as CHGNetModel

        use_device = None
        if resolved_resources.accelerator == "gpu":
            use_device = "cuda"
        elif resolved_resources.accelerator == "mps":
            use_device = "mps"
        elif resolved_resources.accelerator == "cpu":
            use_device = "cpu"

        self._model = CHGNetModel.load(verbose=False, use_device=use_device)
        self._calc = CHGNetCalculator(model=self._model, device=use_device)

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
    
    def compute_atomic_descriptors(
        self, structure: StructureData
    ) -> list[list[float]]:
        from pymatgen.io.ase import AseAtomsAdaptor
        
        atoms = self.convert_structure(structure)

        pymatgen_structure = AseAtomsAdaptor.get_structure(atoms)
        model_results = self._model.predict_structure(pymatgen_structure, return_atom_feas=True)

        return model_results["atom_fea"].tolist()
