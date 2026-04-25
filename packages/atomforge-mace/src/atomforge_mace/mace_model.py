from typing import Literal, Any

from atomforge_core.env.env import EnvironmentSpec
from atomforge_core.model.executor import ModelExecutor
from atomforge_core.model.metadata import ModelMetadata, Reference
from atomforge_core.property import Property
from atomforge_core.resources.resource_caps import ResourceCapabilities
from atomforge_core.model.result import ModelResult
from atomforge_core.model.spec import ModelSpec
from atomforge_core.structure import Structure
from atomforge_core.resources.resource_models import ResolvedResources
from atomforge_core.env.factory import (
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
