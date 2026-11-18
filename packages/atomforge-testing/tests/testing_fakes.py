from typing import Annotated, Literal

from pydantic import PlainSerializer

from atomforge_core.env.env import EnvironmentSpec
from atomforge_core.env.factory import DependencySummary, EnvironmentFactory
from atomforge_core.model.executor import ModelExecutor
from atomforge_core.model.metadata import ModelMetadata
from atomforge_core.model.result import ModelResult
from atomforge_core.model.spec import ModelSpec
from atomforge_core.property import Property
from atomforge_core.resources.resource_caps import ResourceCapabilities
from atomforge_core.resources.resource_probes import ProbeResult
from atomforge_core.structure import StructureData
from atomforge_core.task.executor import TaskExecutionContext, TaskExecutor


class FakeModel(ModelSpec):
    kind: Literal["fake-model"] = "fake-model"


class RequiredFakeModel(ModelSpec):
    kind: Literal["fake-model"] = "fake-model"
    variant: str


class JsonLossyFakeModel(ModelSpec):
    """Round-trips through Python-mode dumps but not through JSON."""

    kind: Literal["fake-model"] = "fake-model"
    variant: Annotated[
        Literal["small"],
        PlainSerializer(lambda value: value.upper(), when_used="json"),
    ] = "small"


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
        python="==3.12.*",
    )

    def build(self, spec: object) -> EnvironmentSpec:
        return EnvironmentSpec(
            name="fake-env",
            python="==3.12.*",
            requirements=["fake-base"],
        )


class BrokenEnvironmentFactory(EnvironmentFactory[object]):
    dependency_summary = DependencySummary(
        base_requirements=(),
        python="==3.12.*",
    )

    def build(self, spec: object) -> EnvironmentSpec:
        return EnvironmentSpec(
            name="broken-env",
            python="==3.12.*",
            requirements=["undeclared-runtime-dependency"],
        )


class NonDeterministicEnvironmentFactory(EnvironmentFactory[object]):
    dependency_summary = DependencySummary(
        base_requirements=(),
        python="==3.12.*",
    )
    counter = 0

    def build(self, spec: object) -> EnvironmentSpec:
        type(self).counter += 1
        return EnvironmentSpec(
            name=f"non-deterministic-env-{type(self).counter}",
            python="==3.12.*",
        )


class FakeTaskOverrideExecutor(TaskExecutor[object, object]):
    def execute(self, spec: object, context: TaskExecutionContext) -> object:
        return object()


def fake_probe(spec: FakeModel) -> ProbeResult:
    return ProbeResult()


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


# Capability contracts (step 2)

ALL_PROPERTIES = frozenset(
    {
        Property.ENERGY,
        Property.FORCES,
        Property.STRESS,
        Property.ENERGIES,
        Property.MAGMOMS,
    }
)


def well_formed_result(
    structure: StructureData, properties: frozenset[Property]
) -> ModelResult:
    n_atoms = len(structure.numbers)
    return ModelResult(
        energy=-1.0 * n_atoms if Property.ENERGY in properties else None,
        forces=[[0.0, 0.0, 0.0] for _ in range(n_atoms)]
        if Property.FORCES in properties
        else None,
        stress=[[0.1, 0.0, 0.0], [0.0, 0.1, 0.0], [0.0, 0.0, 0.1]]
        if Property.STRESS in properties
        else None,
        energies=[-1.0] * n_atoms if Property.ENERGIES in properties else None,
        magmoms=[0.0] * n_atoms if Property.MAGMOMS in properties else None,
    )


class AllPropertiesExecutor(ModelExecutor[FakeModel]):
    def compute(self, structure, properties):
        return well_formed_result(structure, properties)


class NoneStressExecutor(ModelExecutor[FakeModel]):
    def compute(self, structure, properties):
        result = well_formed_result(structure, properties)
        result.stress = None
        return result


class ShortEnergiesExecutor(ModelExecutor[FakeModel]):
    def compute(self, structure, properties):
        result = well_formed_result(structure, properties)
        if result.energies is not None:
            result.energies = result.energies[:-1]
        return result


class VoigtStressExecutor(ModelExecutor[FakeModel]):
    def compute(self, structure, properties):
        result = well_formed_result(structure, properties)
        if result.stress is not None:
            result.stress = [[0.1, 0.1, 0.1, 0.0, 0.0, 0.0]]
        return result


class NanEnergyExecutor(ModelExecutor[FakeModel]):
    def compute(self, structure, properties):
        result = well_formed_result(structure, properties)
        if result.energy is not None:
            result.energy = float("nan")
        return result


class F64FailingExecutor(ModelExecutor[FakeModel]):
    def compute(self, structure, properties):
        if self.resolved_resources.precision == "f64":
            raise RuntimeError("this model cannot run in f64")
        return well_formed_result(structure, properties)


AllSupportedProperties = ALL_PROPERTIES

CpuGpuF32F64Capabilities = ResourceCapabilities(
    accelerator=["cpu", "gpu"], precision=["f32", "f64"]
)
CpuMpsCapabilities = ResourceCapabilities(accelerator=["cpu", "mps"], precision=["f32"])
CpuWithoutPrecisionCapabilities = ResourceCapabilities(accelerator=["cpu"])


class InProcessBackend:
    """Runs the case's model executor in this process, resolving resources
    the simplest way. Records every request."""

    instances: list["InProcessBackend"] = []

    def __init__(self, manifest):
        self.manifest = manifest
        self.requests = []
        type(self).instances.append(self)

    def execute(self, task, model=None, exec_resources=None, timeout=None):
        from atomforge_core.resources.resource_models import (
            ExecutionResources,
            ResolvedResources,
        )

        exec_resources = exec_resources or ExecutionResources()
        self.requests.append((task, model, exec_resources))
        resolved = ResolvedResources(
            accelerator=None
            if exec_resources.accelerator == "default"
            else exec_resources.accelerator,
            precision=None
            if exec_resources.precision == "default"
            else exec_resources.precision,
        )
        executor_cls = self.manifest.executor_cls.load_symbol()
        return executor_cls(model, resolved).compute(task.structure, task.properties)


# Environment profiles


class ProfiledFakeModel(ModelSpec):
    kind: Literal["fake-model"] = "fake-model"
    environment_profile: Literal["tested", "latest"] = "tested"


class ProfileNamedEnvironmentFactory(EnvironmentFactory[object]):
    dependency_summary = DependencySummary(
        base_requirements=("fake-base",),
        python="==3.12.*",
    )
    seen_profiles: list[str] = []

    def build(self, spec) -> EnvironmentSpec:
        type(self).seen_profiles.append(spec.environment_profile)
        return EnvironmentSpec(
            name=f"fake-{spec.environment_profile}",
            python="==3.12.*",
            requirements=["fake-base"],
        )


class LatestBrokenEnvironmentFactory(EnvironmentFactory[object]):
    dependency_summary = DependencySummary(
        base_requirements=("fake-base",),
        python="==3.12.*",
    )

    def build(self, spec) -> EnvironmentSpec:
        if spec.environment_profile == "latest":
            raise RuntimeError("the latest profile cannot be built")
        return EnvironmentSpec(
            name="fake-env", python="==3.12.*", requirements=["fake-base"]
        )
