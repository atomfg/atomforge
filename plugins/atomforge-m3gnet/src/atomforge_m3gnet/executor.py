from atomforge_core.model.executor import ModelExecutor
from atomforge_core.model.result import ModelResult
from atomforge_core.resources.resource_models import ResolvedResources
from atomforge_core.structure import StructureData

from atomforge_m3gnet.spec import M3GNet


class M3GNetExecutor(ModelExecutor[M3GNet]):
    def __init__(self, spec: M3GNet, resolved_resources: ResolvedResources) -> None:
        super().__init__(spec, resolved_resources)
        from m3gnet.models import M3GNet, Potential

        self.potential = Potential(M3GNet.load())

    def convert_structure(self, structure: StructureData):
        from ase import Atoms

        return Atoms(**structure.to_ase_dict())

    def compute(self, structure: StructureData, properties) -> ModelResult:
        atoms = self.convert_structure(structure)
        graph = self.potential.graph_converter(atoms, None)
        graph_list = graph.as_tf().as_list()
        results = self.potential.get_efs_tensor(graph_list, include_stresses=False)
        energy = results[0].numpy().ravel()[0]
        forces = results[1].numpy()
        return ModelResult(energy=energy, forces=forces)
