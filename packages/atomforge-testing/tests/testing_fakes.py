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


# Physics checks (step 3)

SPRING_K = 1.0
SPRING_R0 = 1.2


def spring_result(structure: StructureData, properties) -> ModelResult:
    """Harmonic springs between every pair of atoms: forces are the exact
    negative gradient of the energy, and the energy is invariant under
    translation and rotation."""
    positions = structure.positions
    n_atoms = len(positions)
    energy = 0.0
    energies = [0.0] * n_atoms
    forces = [[0.0, 0.0, 0.0] for _ in range(n_atoms)]
    for i in range(n_atoms):
        for j in range(i + 1, n_atoms):
            d = [positions[i][k] - positions[j][k] for k in range(3)]
            r = sum(c * c for c in d) ** 0.5
            pair = 0.5 * SPRING_K * (r - SPRING_R0) ** 2
            energy += pair
            energies[i] += pair / 2
            energies[j] += pair / 2
            scale = -SPRING_K * (r - SPRING_R0) / r
            for k in range(3):
                forces[i][k] += scale * d[k]
                forces[j][k] -= scale * d[k]
    return ModelResult(
        energy=energy if Property.ENERGY in properties else None,
        forces=forces if Property.FORCES in properties else None,
        energies=energies if Property.ENERGIES in properties else None,
        stress=[[0.1, 0.02, 0.0], [0.02, 0.1, 0.0], [0.0, 0.0, 0.1]]
        if Property.STRESS in properties
        else None,
        magmoms=[0.0] * n_atoms if Property.MAGMOMS in properties else None,
    )


class SpringExecutor(ModelExecutor[FakeModel]):
    def compute(self, structure, properties):
        return spring_result(structure, properties)


class WrongSignForcesExecutor(ModelExecutor[FakeModel]):
    def compute(self, structure, properties):
        result = spring_result(structure, properties)
        if result.forces is not None:
            result.forces = [[-c for c in f] for f in result.forces]
        return result


class NetForceExecutor(ModelExecutor[FakeModel]):
    def compute(self, structure, properties):
        result = spring_result(structure, properties)
        if result.forces is not None:
            result.forces = [[f[0] + 0.1, f[1], f[2]] for f in result.forces]
        return result


class TranslationVariantExecutor(ModelExecutor[FakeModel]):
    """Conservative, with a uniform field along x: the energy changes under a
    translation but not under a rotation about the centroid. Forces and
    per-atom energies include the field consistently."""

    FIELD = 0.1

    def compute(self, structure, properties):
        result = spring_result(structure, properties)
        xs = [p[0] for p in structure.positions]
        if result.energy is not None:
            result.energy += self.FIELD * sum(xs)
        if result.forces is not None:
            for force in result.forces:
                force[0] -= self.FIELD
        if result.energies is not None:
            result.energies = [e + self.FIELD * x for e, x in zip(result.energies, xs)]
        return result


class RotationVariantExecutor(ModelExecutor[FakeModel]):
    """Translation invariant and conservative, but depends on the spread along
    x."""

    def compute(self, structure, properties):
        result = spring_result(structure, properties)
        xs = [p[0] for p in structure.positions]
        mean = sum(xs) / len(xs)
        if result.energy is not None:
            result.energy += 0.1 * sum((x - mean) ** 2 for x in xs)
        if result.forces is not None:
            for force, x in zip(result.forces, xs):
                force[0] -= 0.2 * (x - mean)
        if result.energies is not None:
            result.energies = [
                e + 0.1 * (x - mean) ** 2 for e, x in zip(result.energies, xs)
            ]
        return result


class EnergiesNotSummingExecutor(ModelExecutor[FakeModel]):
    def compute(self, structure, properties):
        result = spring_result(structure, properties)
        if result.energies is not None:
            result.energies = [e + 0.1 for e in result.energies]
        return result


class AsymmetricStressExecutor(ModelExecutor[FakeModel]):
    def compute(self, structure, properties):
        result = spring_result(structure, properties)
        if result.stress is not None:
            result.stress[0][1] += 0.05
        return result


class _ForceNoiseExecutor(ModelExecutor[FakeModel]):
    """Adds +a and -a to every force component on alternate calls, so two
    identical requests differ by 2a. `a` is a fraction of the default f64
    force tolerance."""

    fraction_of_f64_tolerance = 0.0
    calls = 0

    def compute(self, structure, properties):
        from atomforge_testing.physics import DEFAULT_TOLERANCES

        result = spring_result(structure, properties)
        amplitude = self.fraction_of_f64_tolerance * DEFAULT_TOLERANCES["f64"].forces
        sign = 1 if _ForceNoiseExecutor.calls % 2 == 0 else -1
        _ForceNoiseExecutor.calls += 1
        if result.forces is not None:
            result.forces = [[c + sign * amplitude for c in f] for f in result.forces]
        return result


class SmallForceNoiseExecutor(_ForceNoiseExecutor):
    # Two runs differ by half the tolerance; the net force on two atoms is
    # half of it too.
    fraction_of_f64_tolerance = 0.25


class LargeForceNoiseExecutor(_ForceNoiseExecutor):
    # Two runs differ by twice the tolerance.
    fraction_of_f64_tolerance = 1.0


F32F64Capabilities = ResourceCapabilities(accelerator=["cpu"], precision=["f32", "f64"])
F32OnlyCapabilities = ResourceCapabilities(accelerator=["cpu"], precision=["f32"])
SpringSupportedProperties = frozenset(
    {Property.ENERGY, Property.FORCES, Property.ENERGIES, Property.STRESS}
)


WEAK = 1e-9


def _scaled(result, factor):
    if result.energy is not None:
        result.energy *= factor
    if result.forces is not None:
        result.forces = [[factor * c for c in f] for f in result.forces]
    if result.energies is not None:
        result.energies = [factor * e for e in result.energies]
    return result


class WeakSpringExecutor(ModelExecutor[FakeModel]):
    """Consistent, but with forces far too small for a finite-difference
    check to tell a right sign from a wrong one."""

    def compute(self, structure, properties):
        return _scaled(spring_result(structure, properties), WEAK)


class HiddenWrongSignExecutor(ModelExecutor[FakeModel]):
    """Every force has the wrong sign. All are tiny except the y component on
    atom 1, which a check of fixed coordinates (x of the first atom, y of the
    last, z of the middle one) never looks at."""

    FIELD = 1.0

    def compute(self, structure, properties):
        result = _scaled(spring_result(structure, properties), WEAK)
        y1 = structure.positions[1][1]
        if result.energy is not None:
            result.energy += self.FIELD * y1
        if result.energies is not None:
            result.energies[1] += self.FIELD * y1
        if result.forces is not None:
            result.forces[1][1] -= self.FIELD
            result.forces = [[-c for c in f] for f in result.forces]
        return result


# Runtime contracts per profile, and reference values (step 4)


class LatestWrongSignExecutor(ModelExecutor[ProfiledFakeModel]):
    """Exact with the tested profile; forces with the wrong sign with latest."""

    def compute(self, structure, properties):
        result = spring_result(structure, properties)
        if self.spec.environment_profile == "latest" and result.forces is not None:
            result.forces = [[-c for c in f] for f in result.forces]
        return result


class ShiftedSpringExecutor(ModelExecutor[FakeModel]):
    """The spring model with every value of one array shifted by a set
    amount, in every run or only in f32 runs. Tests set the class attributes
    between inner sessions."""

    shifts: dict[str, float] = {}
    f32_shifts: dict[str, float] = {}

    def compute(self, structure, properties):
        result = spring_result(structure, properties)
        shifts = dict(type(self).shifts)
        if self.resolved_resources.precision == "f32":
            for key, value in type(self).f32_shifts.items():
                shifts[key] = shifts.get(key, 0.0) + value
        n_atoms = len(structure.numbers)
        if result.energy is not None:
            result.energy += n_atoms * shifts.get("energy_per_atom", 0.0)
        if result.forces is not None:
            shift = shifts.get("forces", 0.0)
            result.forces = [[c + shift for c in f] for f in result.forces]
        if result.stress is not None:
            shift = shifts.get("stress", 0.0)
            result.stress = [[c + shift for c in row] for row in result.stress]
        return result


class OtherKindFakeModel(ModelSpec):
    kind: Literal["other-fake-model"] = "other-fake-model"


EnergyForcesStress = frozenset({Property.ENERGY, Property.FORCES, Property.STRESS})
