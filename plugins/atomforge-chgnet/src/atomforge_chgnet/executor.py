from atomforge_core.model.executor import ModelExecutor
from atomforge_core.model.result import ModelResult
from atomforge_core.property import Property
from atomforge_core.resources.resource_models import ResolvedResources
from atomforge_core.structure import StructureData

from atomforge_chgnet.spec import CHGNet

class CHGNetExecutor(ModelExecutor[CHGNet]):
    def __init__(self, spec: CHGNet, resolved_resources: ResolvedResources) -> None:
        super().__init__(spec, resolved_resources)
        from chgnet.model import CHGNet as CHGNetModel
        from chgnet.utils import determine_device


        use_device = None
        if resolved_resources.accelerator == "gpu":
            use_device = "cuda"
        elif resolved_resources.accelerator == "mps":
            use_device = "mps"
        elif resolved_resources.accelerator == "cpu":
            use_device = "cpu"

        self.device = determine_device(use_device=use_device)
        self._model = CHGNetModel.load(verbose=False, use_device=self.device)

    def convert_structure(self, structure: StructureData):
        from ase import Atoms

        return Atoms(**structure.to_ase_dict())

    def compute(
        self, structure: StructureData, properties: frozenset[Property]
    ) -> ModelResult:
        from pymatgen.io.ase import AseAtomsAdaptor
        from ase import units

        atoms = self.convert_structure(structure)
        pymatgen_structure = AseAtomsAdaptor.get_structure(atoms)

        graph = self._model.graph_converter(pymatgen_structure)

        if Property.STRESS in properties:
            task = "efs"
        elif Property.FORCES in properties:
            task = "ef"
        else:
            task = "e"

        if Property.MAGMOMS in properties:
            task += "m"


        model_prediction = self._model.predict_graph(
            graph.to(self.device),
            task=task,
            return_site_energies=Property.ENERGIES in properties,
        )

        extensive_factor = len(pymatgen_structure) if self._model.is_intensive else 1
        key_map = dict(
            e=("energy", extensive_factor),
            f=("forces", 1),
            m=("magmoms", 1),
            s=("stress", units.GPa),
        )
        results = {
            long_key: model_prediction[key] * factor
            for key, (long_key, factor) in key_map.items()
            if key in model_prediction
        }

        energy = results.get("energy")
        forces = results.get("forces").tolist() if "forces" in results else None
        magmoms = results.get("magmoms").tolist() if "magmoms" in results else None
        stress = results.get("stress").tolist() if "stress" in results else None
        energies = model_prediction["site_energies"].tolist() if "site_energies" in model_prediction else None

        return ModelResult(
            energy=energy,
            forces=forces,
            magmoms=magmoms,
            stress=stress,
            energies=energies,
        )

    def compute_atomic_descriptors(self, structure: StructureData) -> list[list[float]]:
        from pymatgen.io.ase import AseAtomsAdaptor

        atoms = self.convert_structure(structure)

        pymatgen_structure = AseAtomsAdaptor.get_structure(atoms)
        model_results = self._model.predict_structure(
            pymatgen_structure, return_atom_feas=True
        )

        return model_results["atom_fea"].tolist()
