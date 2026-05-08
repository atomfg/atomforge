from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import os
from pathlib import Path
from numbers import Real
import tomllib

import pytest

from atomforge_core.env.env import EnvironmentSpec
from atomforge_core.env.factory import EnvironmentFactory
from atomforge_core.model.executor import ModelExecutor
from atomforge_core.model.metadata import ModelMetadata
from atomforge_core.model.spec import ModelSpec
from atomforge_core.property import Property
from atomforge_core.registry.model_manifest import ModelManifest
from atomforge_core.resources.resource_caps import ResourceCapabilities
from atomforge_core.resources.resource_models import ExecutionResources
from atomforge_core.structure import StructureData
from atomforge_core.task.executor import TaskExecutor
from atomforge_runtime.registry.model.model_helpers import (
    ManifestToRegistrationConverter,
)
from atomforge_runtime.registry.model.model_registry import ModelRegistry


def default_runtime_structure() -> StructureData:
    from atomforge_testing.structures import small_molecule

    return small_molecule()


def default_runtime_exec_resources() -> ExecutionResources:
    return ExecutionResources(accelerator="cpu", precision="f32")


def default_model_spec_factory(model_cls: type[ModelSpec]) -> ModelSpec:
    return model_cls()


def normalize_distribution_name(name: str) -> str:
    return name.replace("_", "-").lower()


@dataclass(frozen=True)
class ModelManifestCase:
    manifest: ModelManifest
    entry_point_name: str
    entry_point_package: str
    pyproject_path: Path
    expected_entry_point_target: str
    model_spec_factory: Callable[[type[ModelSpec]], ModelSpec] = (
        default_model_spec_factory
    )
    runtime_structure: StructureData | None = None
    runtime_exec_resources: ExecutionResources | None = None


def build_model_spec(case: ModelManifestCase, registration) -> ModelSpec:
    model_spec = case.model_spec_factory(registration.model_spec)
    assert isinstance(model_spec, registration.model_spec)
    return model_spec


class ModelManifestContract:
    manifest_case: ModelManifestCase

    @property
    def case(self) -> ModelManifestCase:
        try:
            return self.manifest_case
        except AttributeError as exc:
            raise AssertionError(
                "ModelManifestContract subclasses must define manifest_case"
            ) from exc

    def _convert_manifest(self):
        converter = ManifestToRegistrationConverter()
        return converter(
            self.case.manifest,
            entry_point_name=self.case.entry_point_name,
            entry_point_package=self.case.entry_point_package,
        )

    def _build_default_model_spec(self):
        registration, _ = self._convert_manifest()
        return build_model_spec(self.case, registration)

    def test_manifest_is_model_manifest(self):
        assert isinstance(self.case.manifest, ModelManifest)

    def test_pyproject_entry_point_targets_manifest(self):
        pyproject = tomllib.loads(self.case.pyproject_path.read_text())
        model_entry_points = (
            pyproject.get("project", {})
            .get("entry-points", {})
            .get("atomforge.model", {})
        )

        assert self.case.entry_point_name in model_entry_points
        assert (
            model_entry_points[self.case.entry_point_name]
            == self.case.expected_entry_point_target
        )

    def test_manifest_converts_to_model_registration(self):
        _, kind = self._convert_manifest()

        assert kind == self.case.manifest.kind

    def test_registration_validate_strict_loads_manifest_paths(self):
        registration, _ = self._convert_manifest()

        registration.validate_strict()


class ModelManifestSymbolContract:
    manifest_case: ModelManifestCase

    @property
    def case(self) -> ModelManifestCase:
        try:
            return self.manifest_case
        except AttributeError as exc:
            raise AssertionError(
                "ModelManifestSymbolContract subclasses must define manifest_case"
            ) from exc

    def test_model_spec_symbol_is_model_spec_subclass(self):
        model_spec = self.case.manifest.model_spec.load_symbol()

        assert isinstance(model_spec, type)
        assert issubclass(model_spec, ModelSpec)

    def test_executor_symbol_is_model_executor_subclass(self):
        executor_cls = self.case.manifest.executor_cls.load_symbol()

        assert isinstance(executor_cls, type)
        assert issubclass(executor_cls, ModelExecutor)

    def test_supported_properties_symbol_is_property_set(self):
        supported_properties = self.case.manifest.supported_properties.load_symbol()

        assert isinstance(supported_properties, frozenset)
        assert all(isinstance(prop, Property) for prop in supported_properties)

    def test_environment_factory_symbol_is_environment_factory_subclass(self):
        environment_factory_cls = (
            self.case.manifest.environment_factory_cls.load_symbol()
        )

        assert isinstance(environment_factory_cls, type)
        assert issubclass(environment_factory_cls, EnvironmentFactory)

    def test_metadata_symbol_is_model_metadata(self):
        metadata = self.case.manifest.metadata.load_symbol()

        assert isinstance(metadata, ModelMetadata)

    def test_resource_capabilities_symbol_is_resource_capabilities(self):
        resource_capabilities = self.case.manifest.resource_capabilities.load_symbol()

        assert isinstance(resource_capabilities, ResourceCapabilities)

    def test_optional_probe_symbol_is_callable_when_present(self):
        probe_path = self.case.manifest.probe
        if probe_path is None:
            pytest.skip("manifest does not declare a resource probe")

        probe = probe_path.load_symbol()

        assert callable(probe)
        assert not isinstance(probe, type)

    def test_task_override_symbols_are_task_executor_subclasses(self):
        if not self.case.manifest.task_overrides:
            pytest.skip("manifest does not declare task override executors")

        for task_kind, executor_path in self.case.manifest.task_overrides.items():
            executor_cls = executor_path.load_symbol()
            assert isinstance(executor_cls, type), task_kind
            assert issubclass(executor_cls, TaskExecutor), task_kind


class ModelEnvironmentContract:
    manifest_case: ModelManifestCase

    @property
    def case(self) -> ModelManifestCase:
        try:
            return self.manifest_case
        except AttributeError as exc:
            raise AssertionError(
                "ModelEnvironmentContract subclasses must define manifest_case"
            ) from exc

    def _convert_manifest(self):
        converter = ManifestToRegistrationConverter()
        return converter(
            self.case.manifest,
            entry_point_name=self.case.entry_point_name,
            entry_point_package=self.case.entry_point_package,
        )

    def _environment_factory(self) -> EnvironmentFactory:
        registration, _ = self._convert_manifest()
        return registration.load_environment_factory()

    def _build_environment_spec(self) -> EnvironmentSpec:
        registration, _ = self._convert_manifest()
        model_spec = build_model_spec(self.case, registration)
        return registration.load_environment_factory()(model_spec)

    def test_environment_factory_builds_model_environment(self):
        env_spec = self._build_environment_spec()

        assert isinstance(env_spec, EnvironmentSpec)

    def test_environment_factory_is_deterministic_for_model_spec(self):
        first = self._build_environment_spec()
        second = self._build_environment_spec()

        assert second == first

    def test_environment_provider_requirements_include_entry_point_package(self):
        env_spec = self._build_environment_spec()
        expected = normalize_distribution_name(self.case.entry_point_package)
        provider_requirements = {
            normalize_distribution_name(requirement)
            for requirement in env_spec.provider_requirements
        }

        assert expected in provider_requirements

    def test_environment_requirements_are_declared_in_dependency_summary(self):
        env_spec = self._build_environment_spec()
        factory = self._environment_factory()
        declared = factory.dependency_summary.declared_requirements()

        assert frozenset(env_spec.requirements).issubset(declared)

    def test_environment_python_matches_dependency_summary(self):
        env_spec = self._build_environment_spec()
        factory = self._environment_factory()
        expected_python = factory.dependency_summary.python

        if expected_python is not None:
            assert env_spec.python == expected_python

    def test_environment_channels_include_dependency_summary_channels(self):
        env_spec = self._build_environment_spec()
        factory = self._environment_factory()
        expected_channels = set(factory.dependency_summary.channels)

        assert expected_channels.issubset(set(env_spec.channels))


def environment_resolution_contract_enabled(request) -> bool:
    markexpr = request.config.option.markexpr
    return "atomforge_environment" in markexpr


def skip_environment_resolution_contract_unless_enabled(request) -> None:
    if not environment_resolution_contract_enabled(request):
        pytest.skip(
            "Run pytest with -m atomforge_environment to run AtomForge "
            "environment resolution contracts"
        )


def default_environment_provider(tmp_path):
    from atomforge.env.uv import UVEnvironmentProvider
    from atomforge.settings.settings import AtomforgeSettings

    settings = AtomforgeSettings()
    if settings.env_provider_kind == "uv":
        return UVEnvironmentProvider(search_path=(tmp_path,), install_path=tmp_path)

    raise AssertionError(f"Unsupported environment provider: {settings.env_provider_kind}")


def format_environment_resolution_failure(result) -> str:
    command = " ".join(result.command or ())
    return "\n".join(
        [
            "Environment resolution failed.",
            f"provider: {result.provider}",
            f"command: {command}",
            f"project_path: {result.project_path}",
            f"message: {result.message}",
            "stdout:",
            result.stdout,
            "stderr:",
            result.stderr,
        ]
    )


class ModelEnvironmentResolutionContract:
    manifest_case: ModelManifestCase

    @property
    def case(self) -> ModelManifestCase:
        try:
            return self.manifest_case
        except AttributeError as exc:
            raise AssertionError(
                "ModelEnvironmentResolutionContract subclasses must define "
                "manifest_case"
            ) from exc

    def _convert_manifest(self):
        converter = ManifestToRegistrationConverter()
        return converter(
            self.case.manifest,
            entry_point_name=self.case.entry_point_name,
            entry_point_package=self.case.entry_point_package,
        )

    def _build_environment_spec(self) -> EnvironmentSpec:
        registration, _ = self._convert_manifest()
        model_spec = build_model_spec(self.case, registration)
        return registration.load_environment_factory()(model_spec)

    @pytest.mark.atomforge_environment
    def test_environment_resolves_with_default_provider(self, request, tmp_path):
        skip_environment_resolution_contract_unless_enabled(request)
        provider = default_environment_provider(tmp_path)
        env_spec = self._build_environment_spec()

        result = provider.resolve_environment(env_spec)

        assert result.success, format_environment_resolution_failure(result)


class ModelSpecContract:
    manifest_case: ModelManifestCase

    @property
    def case(self) -> ModelManifestCase:
        try:
            return self.manifest_case
        except AttributeError as exc:
            raise AssertionError(
                "ModelSpecContract subclasses must define manifest_case"
            ) from exc

    def _convert_manifest(self):
        converter = ManifestToRegistrationConverter()
        return converter(
            self.case.manifest,
            entry_point_name=self.case.entry_point_name,
            entry_point_package=self.case.entry_point_package,
        )

    def _build_model_spec(self):
        registration, _ = self._convert_manifest()
        return build_model_spec(self.case, registration)

    def test_model_spec_factory_returns_registered_model_spec(self):
        registration, _ = self._convert_manifest()
        model_spec = build_model_spec(self.case, registration)

        assert isinstance(model_spec, registration.model_spec)

    def test_model_spec_kind_matches_manifest_kind(self):
        model_spec = self._build_model_spec()

        assert model_spec.kind == self.case.manifest.kind

    def test_model_spec_round_trips_through_model_dump(self):
        registration, _ = self._convert_manifest()
        model_spec = build_model_spec(self.case, registration)

        restored = registration.model_spec.model_validate(model_spec.model_dump())

        assert restored.model_dump() == model_spec.model_dump()


class ModelRegistryContract:
    manifest_case: ModelManifestCase

    @property
    def case(self) -> ModelManifestCase:
        try:
            return self.manifest_case
        except AttributeError as exc:
            raise AssertionError(
                "ModelRegistryContract subclasses must define manifest_case"
            ) from exc

    def _discovered_registration(self):
        registry = ModelRegistry.default()
        return registry.get(self.case.manifest.kind)

    def test_model_is_discoverable_by_default_registry(self):
        registration = self._discovered_registration()

        assert registration is not None

    def test_discovered_registration_kind_matches_manifest(self):
        registration = self._discovered_registration()

        assert registration.kind == self.case.manifest.kind

    def test_discovered_registration_source_includes_entry_point_package(self):
        registration = self._discovered_registration()
        expected = normalize_distribution_name(self.case.entry_point_package)
        sources = {
            normalize_distribution_name(source) for source in registration.source
        }

        assert expected in sources

    def test_discovered_registration_model_spec_matches_manifest_path(self):
        registration = self._discovered_registration()

        assert registration.model_spec is self.case.manifest.model_spec.load_symbol()


def runtime_contract_enabled() -> bool:
    return os.environ.get("ATOMFORGE_RUN_RUNTIME_TESTS") == "1"


def skip_runtime_contract_unless_enabled() -> None:
    if not runtime_contract_enabled():
        pytest.skip(
            "Set ATOMFORGE_RUN_RUNTIME_TESTS=1 to run AtomForge runtime contracts"
        )


def assert_energy_result(result) -> None:
    assert result.energy is not None
    assert isinstance(result.energy, Real)


def assert_forces_result(result, structure: StructureData) -> None:
    assert result.forces is not None
    assert isinstance(result.forces, list)
    assert len(result.forces) == len(structure.numbers)
    assert all(isinstance(force, list) for force in result.forces)
    assert all(len(force) == 3 for force in result.forces)


@pytest.mark.atomforge_runtime
class ModelSinglePointRuntimeContract:
    manifest_case: ModelManifestCase

    @property
    def case(self) -> ModelManifestCase:
        try:
            return self.manifest_case
        except AttributeError as exc:
            raise AssertionError(
                "ModelSinglePointRuntimeContract subclasses must define manifest_case"
            ) from exc

    def _convert_manifest(self):
        converter = ManifestToRegistrationConverter()
        return converter(
            self.case.manifest,
            entry_point_name=self.case.entry_point_name,
            entry_point_package=self.case.entry_point_package,
        )

    def _build_runtime_model_spec(self):
        registration, _ = self._convert_manifest()
        return build_model_spec(self.case, registration)

    def _runtime_structure(self) -> StructureData:
        if self.case.runtime_structure is not None:
            return self.case.runtime_structure
        return default_runtime_structure()

    def _runtime_exec_resources(self) -> ExecutionResources:
        if self.case.runtime_exec_resources is not None:
            return self.case.runtime_exec_resources
        return default_runtime_exec_resources()

    def _execute_single_point(self, properties: frozenset[Property]):
        from atomforge.backend.subprocess import SubprocessBackend
        from atomforge_builtins.task.single_point import SinglePoint

        structure = self._runtime_structure()
        task = SinglePoint(structure=structure, properties=properties)
        model = self._build_runtime_model_spec()
        resources = self._runtime_exec_resources()

        backend = SubprocessBackend()
        return backend.execute(task, model=model, exec_resources=resources)

    def test_single_point_energy_executes_if_declared(self):
        skip_runtime_contract_unless_enabled()
        registration, _ = self._convert_manifest()
        supported_properties = registration.load_supported_properties()
        if Property.ENERGY not in supported_properties:
            pytest.skip(f"{registration.kind} does not declare energy support")

        result = self._execute_single_point(frozenset({Property.ENERGY}))

        assert_energy_result(result)

    def test_single_point_forces_shape_if_declared(self):
        skip_runtime_contract_unless_enabled()
        registration, _ = self._convert_manifest()
        supported_properties = registration.load_supported_properties()
        if Property.FORCES not in supported_properties:
            pytest.skip(f"{registration.kind} does not declare forces support")

        structure = self._runtime_structure()
        result = self._execute_single_point(frozenset({Property.FORCES}))

        assert_forces_result(result, structure)
