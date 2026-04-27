from typing import Literal

from atomforge_core.env.env import EnvironmentSpec
from atomforge_core.model.executor import ModelExecutor
from atomforge_core.model.metadata import ModelMetadata, Reference
from atomforge_core.property import Property
from atomforge_core.resources.resource_caps import ResourceCapabilities
from atomforge_core.model.result import ModelResult
from atomforge_core.model.spec import ModelSpec
from atomforge_core.structure import StructureData
from atomforge_core.resources.resource_models import ResolvedResources
from atomforge_core.env.factory import (
    EnvironmentFactory,
    DependencySummary,
)

model_kind = "mg3net"
MG3NetSupportedProperties = frozenset({Property.ENERGY, Property.FORCES})


class MG3Net(ModelSpec):
    kind: Literal["mg3net"] = model_kind


MG3NetResourceCapabilities = ResourceCapabilities(
    accelerator=["cpu"],
)

MG3NetMetadata = ModelMetadata(
    id=model_kind,
    name="MG3Net",
    method_family="mlip",
    references=(
        Reference(
            label="GitHub Repository",
            url="https://github.com/materialyzeai/m3gnet",
            kind="repo",
        ),
        Reference(label="Paper", url="https://arxiv.org/abs/2202.02450", kind="paper"),
    ),
)

# The first three here are MG3Nets own specifications. But because that is not 
# actually specific enough it breaks without specifying the keras version. 
requirements = [
    "m3gnet==0.2.4",
    "ase==3.22.1",
    "tensorflow>=2.13,<2.16",
    "keras<3",
]


class MG3NetEnvironmentFactory(EnvironmentFactory[MG3Net]):
    dependency_summary = DependencySummary(
        base_requirements=tuple(requirements), python="3.10"
    )

    def build(self, spec: MG3Net) -> EnvironmentSpec:
        return EnvironmentSpec(
            name=spec.kind,
            python="3.10",
            requirements=requirements,
        )

class MG3NetExecutor(ModelExecutor[MG3Net]):
    def __init__(
        self, spec: MG3Net, resolved_resources: ResolvedResources
    ) -> None:
        super().__init__(spec, resolved_resources)
        from m3gnet.models import M3GNet, Potential
        self.potential = Potential(M3GNet.load())

    def structure_conversion(self, structure: StructureData):
        from ase import Atoms
        atoms = Atoms(**structure.to_ase_dict())
        return atoms

    def compute(self, structure: StructureData, properties) -> ModelResult:
        atoms = self.structure_conversion(structure)
        graph = self.potential.graph_converter(atoms, None)
        graph_list = graph.as_tf().as_list()
        results = self.potential.get_efs_tensor(graph_list, include_stresses=False)
        energy = results[0].numpy().ravel()[0]
        forces = results[1].numpy()
        return ModelResult(energy=energy, forces=forces)
