from typing import Literal, Any

from atomforge.env.base.env import EnvironmentSpec
from atomforge.model.core.executor import ModelExecutor
from atomforge.model.core.metadata import ModelMetadata, Reference
from atomforge.model.core.property import Property
from atomforge.model.core.resource_caps import ResourceCapabilities
from atomforge.model.core.result import ModelResult
from atomforge.model.core.spec import ModelSpec
from atomforge.structure import Structure
from atomforge.task.core.resources import ResolvedResources
from atomforge.env.base.factory import (
    environment_factory_from_callable,
    DependencySummary,
)


model_kind = "mace"
MACESupportedProperties = frozenset({Property.ENERGY, Property.FORCES})

MACEResourceCapabilities = ResourceCapabilities(
    accelerator=["cpu", "gpu"],
    precision=["f32", "f64"],
)


class MACE(ModelSpec):
    kind: Literal["mace"] = model_kind
    model: str = "medium"
    dispersion: bool = False


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


MACEEnvironmentFactory = environment_factory_from_callable(
    lambda spec: EnvironmentSpec(
        name=spec.kind,
        python="python3.12",
        requirements=["mace-torch", "torch"],
    ),
    DependencySummary(base_requirements=["mace-torch", "torch"], python="python3.12"),
)

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
        # Set the precision based on the ResolvedResources
        if resolved_resources.precision is not None:
            if resolved_resources.precision == "f64":
                default_dtype = "float64"
            elif resolved_resources.precision == "f32":
                default_dtype = "float32"
        else:
            default_dtype = "float32"

        # Set device based on the ResolvedResources
        if resolved_resources.accelerator == "gpu":
            device = "cuda"
        elif resolved_resources.accelerator == "mps":
            device = "mps"
        elif resolved_resources.accelerator == "cpu":
            device = "cpu"
        else:
            device = None

        return {"default_dtype": default_dtype, "device": device}

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
