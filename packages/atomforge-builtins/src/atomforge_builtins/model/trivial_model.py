from typing import Literal

from atomforge_core.env.env import EnvironmentSpec
from atomforge_core.model.executor import ModelExecutor
from atomforge_core.model.metadata import ModelMetadata
from atomforge_core.property import Property
from atomforge_core.registry.model_manifest import ModelManifest
from atomforge_core.resources.resource_caps import ResourceCapabilities
from atomforge_core.model.result import ModelResult
from atomforge_core.model.spec import ModelSpec
from atomforge_core.structure import StructureData
from atomforge_core.resources.resource_models import ResolvedResources
from atomforge_core.env.factory import EnvironmentFactory, DependencySummary

description = """A trivial model for testing the runtime: zero forces and an energy
linear in the number of atoms. Needs only numpy."""

model_kind = "trivial"
TrivialSupportedProperties = frozenset({Property.ENERGY, Property.FORCES})


class Trivial(ModelSpec):
    environment_profile: Literal["tested"] = "tested"
    kind: Literal["trivial"] = model_kind
    scale: float = 1.0


TrivialMetadata = ModelMetadata(
    id=model_kind,
    name="Trivial Model",
    method_family="empirical",
    description=description,
)


TrivialCapabilities = ResourceCapabilities(accelerator=["cpu"], precision=None)

TrivialEnvironmentProfiles = {
    "tested": EnvironmentSpec(
        name=model_kind, python="==3.12.*", requirements=["numpy"]
    )
}


class TrivialEnvironmentFactory(EnvironmentFactory[Trivial]):
    dependency_summary = DependencySummary(
        base_requirements=("numpy",),
        python="==3.12.*",
    )

    def build(self, spec: Trivial) -> EnvironmentSpec:
        return TrivialEnvironmentProfiles[spec.environment_profile]


class TrivialExecutor(ModelExecutor[Trivial]):
    def __init__(self, spec: Trivial, resolved_resources: ResolvedResources) -> None:
        super().__init__(spec, resolved_resources)

    def compute(self, structure: StructureData, properties: frozenset[Property]):

        # Calculate forces if requested, otherwise set to None to avoid unnecessary computation
        if Property.FORCES in properties:
            import numpy as np

            forces = np.zeros((len(structure.numbers), 3))
        else:
            forces = None

        # Calculate energy if requested, otherwise set to None to avoid unnecessary computation
        # If forces were requested ASE will have already calculated the energy, so this won't trigger an additional calculation
        if Property.ENERGY in properties:
            energy = float(
                len(structure.numbers) * -0.1 * self.spec.scale
            )  # Dummy energy calculation based on number of atoms
        else:
            energy = None

        return ModelResult(
            energy=energy,
            forces=forces,
        )


trivial_manifest = ModelManifest(
    kind="trivial",
    model_spec="atomforge_builtins.model.trivial_model:Trivial",
    executor_cls="atomforge_builtins.model.trivial_model:TrivialExecutor",
    supported_properties="atomforge_builtins.model.trivial_model:TrivialSupportedProperties",
    environment_factory_cls="atomforge_builtins.model.trivial_model:TrivialEnvironmentFactory",
    metadata="atomforge_builtins.model.trivial_model:TrivialMetadata",
    resource_capabilities="atomforge_builtins.model.trivial_model:TrivialCapabilities",
    distribution=["atomforge_builtins"],
)
