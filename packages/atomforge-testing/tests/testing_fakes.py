from typing import Literal

from atomforge_core.env.env import EnvironmentSpec
from atomforge_core.env.factory import DependencySummary, EnvironmentFactory
from atomforge_core.model.executor import ModelExecutor
from atomforge_core.model.metadata import ModelMetadata
from atomforge_core.model.result import ModelResult
from atomforge_core.model.spec import ModelSpec
from atomforge_core.property import Property
from atomforge_core.resources.resource_caps import ResourceCapabilities
from atomforge_core.structure import StructureData


class FakeModel(ModelSpec):
    kind: Literal["fake-model"] = "fake-model"


class RequiredFakeModel(ModelSpec):
    kind: Literal["fake-model"] = "fake-model"
    variant: str


class MismatchedKindFakeModel(ModelSpec):
    kind: Literal["other-model"] = "other-model"


class FakeModelExecutor(ModelExecutor[FakeModel]):
    def compute(
        self, structure: StructureData, properties: frozenset[Property]
    ) -> ModelResult:
        energy = 1.0 if Property.ENERGY in properties else None
        forces = (
            [[0.0, 0.0, 0.0] for _ in structure.numbers]
            if Property.FORCES in properties
            else None
        )
        return ModelResult(energy=energy, forces=forces)


class FakeEnvironmentFactory(EnvironmentFactory[object]):
    dependency_summary = DependencySummary(
        base_requirements=("fake-base",),
        python="3.12",
    )

    def build(self, spec: object) -> EnvironmentSpec:
        return EnvironmentSpec(
            name="fake-env",
            python="3.12",
            requirements=["fake-base"],
        )


class BrokenEnvironmentFactory(EnvironmentFactory[object]):
    dependency_summary = DependencySummary(
        base_requirements=(),
        python="3.12",
    )

    def build(self, spec: object) -> EnvironmentSpec:
        return EnvironmentSpec(
            name="broken-env",
            python="3.12",
            requirements=["undeclared-runtime-dependency"],
        )


FakeSupportedProperties = frozenset({Property.ENERGY, Property.FORCES})
FakeMetadata = ModelMetadata(
    id="fake-model",
    name="Fake Model",
    method_family="empirical",
    description="Testing fake",
)
FakeResourceCapabilities = ResourceCapabilities(
    accelerator=["cpu"],
    precision=["f32"],
)
