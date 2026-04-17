from typing import Literal

from atomforge.backend.base.resources import ResolvedResources
from atomforge.env.base.env import EnvironmentSpec
from atomforge.model.base.executor import ModelExecutor
from atomforge.model.base.metadata import ModelMetadata, Reference
from atomforge.model.base.property import Property
from atomforge.model.base.resource_caps import ResourceCapabilities
from atomforge.model.base.result import ModelResult
from atomforge.model.base.spec import ModelSpec
from atomforge.structure import Structure

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


def chgnet_environment(spec: CHGNet) -> EnvironmentSpec:
    return EnvironmentSpec(name=spec.kind, python="python3.12", requirements=["chgnet"])


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

    def compute(
        self, structure: Structure, properties: frozenset[Property]
    ) -> ModelResult:
        atoms = structure.to_ase()
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
