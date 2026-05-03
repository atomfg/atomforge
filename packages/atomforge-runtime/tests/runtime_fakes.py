from __future__ import annotations

from dataclasses import replace
from typing import Literal

from atomforge_core.env.env import EnvironmentSpec
from atomforge_core.env.factory import DependencySummary, EnvironmentFactory
from atomforge_core.model.executor import ModelExecutor
from atomforge_core.model.metadata import ModelMetadata
from atomforge_core.model.result import ModelResult
from atomforge_core.model.spec import ModelSpec
from atomforge_core.property import Property
from atomforge_core.resources.resource_caps import ResourceCapabilities
from atomforge_core.resources.resource_models import ResolvedResources
from atomforge_core.resources.resource_probes import ProbeResult
from atomforge_core.structure import StructureData
from atomforge_core.task.capability import TaskCapabilitySpec
from atomforge_core.task.executability import CompatibilityCheck
from atomforge_core.task.executor import TaskExecutionContext
from atomforge_core.task.result import TaskResult
from atomforge_core.task.spec import TaskSpec
from atomforge_runtime.registry.model.model_registration import ModelRegistration
from atomforge_runtime.registry.model.model_registry import ModelRegistry
from atomforge_runtime.registry.task.task_registry import TaskRegistry
from atomforge_runtime.registry.task.task_registration import TaskRegistration


class FakeModel(ModelSpec):
    kind: Literal["fake-model"] = "fake-model"
    scale: float = 1.0


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


class FakeModelExecutor(ModelExecutor[FakeModel]):
    def compute(
        self, structure: StructureData, properties: frozenset[Property]
    ) -> ModelResult:
        energy = None
        forces = None
        if Property.ENERGY in properties:
            energy = -0.5 * self.spec.scale * len(structure.numbers)
        if Property.FORCES in properties:
            forces = [[0.0, 0.0, 0.0] for _ in structure.numbers]
        return ModelResult(energy=energy, forces=forces)


class FakeTask(TaskSpec):
    kind: Literal["fake-task"] = "fake-task"
    structure: StructureData
    allow_execution: bool = True
    minimum_override_scale: float = 0.0

    def required_model_properties(self) -> frozenset[Property]:
        return frozenset({Property.ENERGY, Property.FORCES})


class FakeTaskResult(TaskResult):
    kind: Literal["fake-task"] = "fake-task"
    energy: float | None
    forces: list[list[float]] | None


class FakeTaskOnly(TaskSpec):
    requires_model = False
    kind: Literal["fake-task-only"] = "fake-task-only"
    value: int = 1

    def required_model_properties(self) -> frozenset[Property]:
        return frozenset()


class FakeTaskOnlyResult(TaskResult):
    kind: Literal["fake-task-only"] = "fake-task-only"
    doubled_value: int
    used_model: bool
    resource_accelerator: str | None


class FakeTaskExecutor:
    @classmethod
    def check_compatibility(
        cls, spec: FakeTask, context: TaskExecutionContext
    ) -> CompatibilityCheck:
        if not spec.allow_execution:
            return CompatibilityCheck(
                ok=False,
                reason="FakeTaskExecutor does not support allow_execution=False",
            )
        return CompatibilityCheck(ok=True)

    def execute(
        self, spec: FakeTask, context: TaskExecutionContext
    ) -> FakeTaskResult:
        if context.model_executor is None:
            raise ValueError("FakeTask requires a model executor")
        model_executor = context.model_executor
        result = model_executor.compute(
            spec.structure,
            frozenset({Property.ENERGY, Property.FORCES}),
        )
        return FakeTaskResult(energy=result.energy, forces=result.forces)


class FakeOverrideTaskExecutor(FakeTaskExecutor):
    @classmethod
    def check_compatibility(
        cls, spec: FakeTask, context: TaskExecutionContext
    ) -> CompatibilityCheck:
        model_executor = context.model_executor
        if model_executor is None:  # Defensive; worker_checks should prevent this path.
            return CompatibilityCheck(
                ok=False,
                reason="FakeOverrideTaskExecutor requires a model executor",
            )
        if model_executor.spec.scale < spec.minimum_override_scale:
            return CompatibilityCheck(
                ok=False,
                reason=(
                    f"FakeOverrideTaskExecutor requires model scale >= "
                    f"{spec.minimum_override_scale}"
                ),
            )
        return CompatibilityCheck(ok=True)


class FakeTaskOnlyExecutor:
    @classmethod
    def check_compatibility(
        cls, spec: FakeTaskOnly, context: TaskExecutionContext
    ) -> CompatibilityCheck:
        if context.model_executor is not None:
            return CompatibilityCheck(
                ok=False,
                reason="FakeTaskOnlyExecutor does not expect a model executor",
            )
        return CompatibilityCheck(ok=True)

    def execute(
        self, spec: FakeTaskOnly, context: TaskExecutionContext
    ) -> FakeTaskOnlyResult:
        return FakeTaskOnlyResult(
            doubled_value=spec.value * 2,
            used_model=context.model_executor is not None,
            resource_accelerator=(
                None
                if context.resolved_resources is None
                else context.resolved_resources.accelerator
            ),
        )


FakeSupportedProperties = frozenset({Property.ENERGY, Property.FORCES})
EmptySupportedProperties = frozenset()
FakeCapabilitySpec = TaskCapabilitySpec(
    required=frozenset({Property.ENERGY, Property.FORCES}),
    optional=frozenset(),
)
FakeTaskOnlyCapabilitySpec = TaskCapabilitySpec(
    required=frozenset(),
    optional=frozenset(),
)
FakeMetadata = ModelMetadata(
    id="fake-model",
    name="Fake Model",
    method_family="empirical",
    description="Runtime test double",
)
FakeResourceCapabilities = ResourceCapabilities(
    accelerator=["cpu", "gpu"],
    precision=["f32", "f64"],
)


def fake_probe(spec: FakeModel) -> ProbeResult:
    return ProbeResult(available_accelerators=frozenset({"cpu", "gpu"}))


def build_model_registration() -> ModelRegistration:
    from atomforge_core.registry.symbol_path import SymbolPath

    return ModelRegistration(
        kind="fake-model",
        model_spec=FakeModel,
        metadata_path=SymbolPath("runtime_fakes:FakeMetadata"),
        executor_class_path=SymbolPath("runtime_fakes:FakeModelExecutor"),
        supported_properties_path=SymbolPath("runtime_fakes:FakeSupportedProperties"),
        environment_factory_path=SymbolPath("runtime_fakes:FakeEnvironmentFactory"),
        resource_capabilities_path=SymbolPath("runtime_fakes:FakeResourceCapabilities"),
        probe_path=SymbolPath("runtime_fakes:fake_probe"),
        task_overrides={"fake-task": SymbolPath("runtime_fakes:FakeOverrideTaskExecutor")},
        source=["runtime-test-plugin"],
    )


def build_task_registration() -> TaskRegistration:
    from atomforge_core.registry.symbol_path import SymbolPath

    return TaskRegistration(
        kind="fake-task",
        spec_model=FakeTask,
        result_model_path=SymbolPath("runtime_fakes:FakeTaskResult"),
        executor_class_path=SymbolPath("runtime_fakes:FakeTaskExecutor"),
        capability_spec_path=SymbolPath("runtime_fakes:FakeCapabilitySpec"),
        environment_factory_path=SymbolPath("runtime_fakes:FakeEnvironmentFactory"),
        source=["runtime-test-plugin"],
    )


def build_task_only_registration() -> TaskRegistration:
    from atomforge_core.registry.symbol_path import SymbolPath

    return TaskRegistration(
        kind="fake-task-only",
        spec_model=FakeTaskOnly,
        result_model_path=SymbolPath("runtime_fakes:FakeTaskOnlyResult"),
        executor_class_path=SymbolPath("runtime_fakes:FakeTaskOnlyExecutor"),
        capability_spec_path=SymbolPath("runtime_fakes:FakeTaskOnlyCapabilitySpec"),
        environment_factory_path=SymbolPath("runtime_fakes:FakeEnvironmentFactory"),
        source=["runtime-test-plugin"],
    )


def build_model_registry() -> ModelRegistry:
    registry = ModelRegistry()
    registration = build_model_registration()
    registry._register(registration, registration.kind)
    return registry


def build_task_registry() -> TaskRegistry:
    registry = TaskRegistry()
    for registration in (build_task_registration(), build_task_only_registration()):
        registry._register(registration, registration.kind)
    return registry


def build_broken_model_registration(**kwargs) -> ModelRegistration:
    return replace(build_model_registration(), **kwargs)


def build_broken_task_registration(**kwargs) -> TaskRegistration:
    return replace(build_task_registration(), **kwargs)
