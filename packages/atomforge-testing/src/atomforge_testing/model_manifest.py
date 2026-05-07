from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import os
from pathlib import Path
from numbers import Real
import tomllib

import pytest

from atomforge_core.env.env import EnvironmentSpec
from atomforge_core.model.spec import ModelSpec
from atomforge_core.property import Property
from atomforge_core.registry.model_manifest import ModelManifest
from atomforge_core.resources.resource_models import ExecutionResources
from atomforge_core.structure import StructureData
from atomforge_runtime.registry.model.model_helpers import (
    ManifestToRegistrationConverter,
)


def default_runtime_structure() -> StructureData:
    return StructureData(
        positions=[[4.5, 0.0, 0.0], [5.5, 0.0, 0.0]],
        cell=[[10.0, 0.0, 0.0], [0.0, 10.0, 0.0], [0.0, 0.0, 10.0]],
        numbers=[1, 8],
        pbc=[False, False, False],
    )


def default_runtime_exec_resources() -> ExecutionResources:
    return ExecutionResources(accelerator="cpu", precision="f32")


def default_model_spec_factory(model_cls: type[ModelSpec]) -> ModelSpec:
    return model_cls()


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

    def test_environment_factory_builds_default_model_environment(self):
        registration, _ = self._convert_manifest()
        model_spec = self._build_default_model_spec()

        env_spec = registration.load_environment_factory()(model_spec)

        assert isinstance(env_spec, EnvironmentSpec)


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
