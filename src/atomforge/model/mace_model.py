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

model_kind = "mace"
MACESupportedProperties = frozenset({Property.ENERGY, Property.FORCES})


class MACE(ModelSpec):
    kind: Literal["mace"] = model_kind
    model: str = "medium"
    dispersion: bool = False
    default_dtype: str = "float32"


MACEMetadata = ModelMetadata(
    id=model_kind,
    name="MACE",
    method_family="mlip",
    references=(
        Reference(
            label="GitHub Repository",
            url="https://github.com/ACEsuit/mace",
            kind="repo",
        ),
        Reference(
            label="Paper",
            url="https://openreview.net/forum?id=YPpSngE-ZU",
            kind="paper",
        ),
    ),
)


def mace_environment(spec: MACE) -> EnvironmentSpec:
    return EnvironmentSpec(
        name=spec.kind,
        python="python3.12",
        requirements=["mace-torch", "torch"],
    )


class MACEExecutor(ModelExecutor[MACE]):
    def __init__(self, spec: MACE) -> None:
        super().__init__(spec)
        from mace.calculators import mace_mp

        self._calc = mace_mp(
            model=spec.model,
            dispersion=spec.dispersion,
            default_dtype=spec.default_dtype,
        )

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

    spec = MACE()
    executor = MACEExecutor(spec)
    structure = Structure.from_ase(molecule("H2O"))
    result = executor.compute(structure, {Property.ENERGY, Property.FORCES})
    print(result)
