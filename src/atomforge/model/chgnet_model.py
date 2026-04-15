from typing import Literal

from atomforge.env import EnvironmentSpec
from atomforge.model.base import (
    ModelExecutor,
    ModelMetadata,
    ModelResult,
    ModelSpec,
    Property,
    Reference,
)
from atomforge.structure import Structure

model_kind = "chgnet"
CHGNetSupportedProperties = frozenset({Property.ENERGY, Property.FORCES})


class CHGNet(ModelSpec):
    kind: Literal["chgnet"] = model_kind


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
    def __init__(self, spec: CHGNet) -> None:
        super().__init__(spec)
        from chgnet.model.dynamics import CHGNetCalculator

        self._calc = CHGNetCalculator()

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


if __name__ == "__main__":
    from ase.build import molecule
    from rich import print

    spec = CHGNet()
    executor = CHGNetExecutor(spec)
    atoms = molecule("H2O")
    atoms.cell = [10, 10, 10]
    structure = Structure.from_ase(atoms)
    result = executor.compute(structure, {Property.ENERGY, Property.FORCES})
    print(result)
