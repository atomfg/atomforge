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
    environment_factory_from_callable,
    DependencySummary,
)

model_kind = "chgnet"
CHGNetSupportedProperties = frozenset({Property.ENERGY, Property.FORCES})


class CHGNet(ModelSpec):
    kind: Literal["chgnet"] = model_kind


CHGNetResourceCapabilities = ResourceCapabilities(
    accelerator=["cpu", "gpu", "mps"],
)

CHGNetMetadata = ModelMetadata(
    id=model_kind,
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


CHGNetEnvironmentFactory = environment_factory_from_callable(
    lambda spec: EnvironmentSpec(name=spec.kind, python=">=3.12", requirements=["chgnet", "ase"]),
    DependencySummary(base_requirements=["chgnet", "ase"], python=">=3.12"),
)


class CHGNetExecutor(ModelExecutor[CHGNet]):
    def __init__(self, spec: CHGNet, resolved_resources: ResolvedResources) -> None:
        super().__init__(spec, resolved_resources)
        from chgnet.model.dynamics import CHGNetCalculator

        use_device = None
        if resolved_resources.accelerator == "gpu":
            use_device = "cuda"
        elif resolved_resources.accelerator == "mps":
            use_device = "mps"
        elif resolved_resources.accelerator == "cpu":
            use_device = "cpu"

        self._calc = CHGNetCalculator(use_device=use_device)

    def structure_conversion(self, structure: StructureData):
        from ase import Atoms
        atoms = Atoms(**structure.to_ase_dict())
        return atoms

    def compute(
        self, structure: StructureData, properties: frozenset[Property]
    ) -> ModelResult:
        atoms = self.structure_conversion(structure)
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
