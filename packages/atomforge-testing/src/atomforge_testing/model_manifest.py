from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
import tomllib

import pytest
from pydantic import ValidationError

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

from atomforge_testing import physics
from atomforge_testing.physics import ModelPhysics, ReferenceTolerances, Tolerances
from atomforge_testing.capabilities import (  # noqa: F401 - re-exported
    PROPERTY_CHECKS,
    assert_energies_result,
    assert_energy_result,
    assert_forces_result,
    assert_magmoms_result,
    assert_stress_result,
)


def default_runtime_structure() -> StructureData:
    from atomforge_testing.structures import small_molecule

    return small_molecule()


def default_runtime_exec_resources() -> ExecutionResources:
    return ExecutionResources(accelerator="cpu", precision="f32")


def default_model_spec_factory(model_cls: type[ModelSpec]) -> ModelSpec:
    return model_cls()


def normalize_distribution_name(name: str) -> str:
    return name.replace("_", "-").lower()


PHYSICS_STRUCTURE_NAMES = ("molecule", "slab", "bulk")


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
    runtime_skip_reason: str | None = None
    # Per-precision ("f32", "f64") replacements for the physics checks'
    # default tolerances (atomforge_testing.physics.DEFAULT_TOLERANCES).
    tolerances: Mapping[str, Tolerances] | None = None
    # Physical properties the model has; the physics checks that rely on a
    # property it declares absent are skipped.
    physics: ModelPhysics = ModelPhysics()
    # Structures for the physics checks, by name ("molecule", "slab", "bulk").
    # None uses atomforge_testing.structures.reference_structures(); a mapping
    # replaces them, and the checks of a structure it leaves out are skipped.
    physics_structures: Mapping[str, StructureData] | None = None
    # Replacement for the reference comparison's tolerances
    # (atomforge_testing.physics.REFERENCE_TOLERANCES).
    reference_tolerances: ReferenceTolerances | None = None

    def __post_init__(self) -> None:
        if self.physics_structures is not None:
            unknown = set(self.physics_structures) - set(PHYSICS_STRUCTURE_NAMES)
            if unknown:
                raise ValueError(
                    f"unknown physics structure names {sorted(unknown)}; "
                    f"expected some of {list(PHYSICS_STRUCTURE_NAMES)}"
                )


def build_model_spec(case: ModelManifestCase, registration) -> ModelSpec:
    model_spec = case.model_spec_factory(registration.model_spec)
    assert isinstance(model_spec, registration.model_spec)
    return model_spec


class _ManifestCaseContract:
    """Helpers shared by every contract. Subclasses set ``manifest_case``."""

    manifest_case: ModelManifestCase

    @property
    def case(self) -> ModelManifestCase:
        try:
            return self.manifest_case
        except AttributeError as exc:
            raise AssertionError(
                f"{type(self).__name__} must define manifest_case"
            ) from exc

    def _convert_manifest(self):
        converter = ManifestToRegistrationConverter()
        return converter(
            self.case.manifest,
            entry_point_name=self.case.entry_point_name,
            entry_point_package=self.case.entry_point_package,
        )

    def _build_model_spec(self, environment_profile: str | None = None) -> ModelSpec:
        """The case's representative spec, optionally with another
        environment profile."""
        registration, _ = self._convert_manifest()
        model_spec = build_model_spec(self.case, registration)
        if environment_profile is None:
            return model_spec
        payload = model_spec.model_dump()
        payload["environment_profile"] = environment_profile
        return type(model_spec).model_validate(payload)

    def _build_environment_spec(
        self, environment_profile: str | None = None
    ) -> EnvironmentSpec:
        model_spec = self._build_model_spec(environment_profile)
        return self._environment_factory()(model_spec)

    def _environment_factory(self) -> EnvironmentFactory:
        registration, _ = self._convert_manifest()
        return registration.load_environment_factory()


class ModelManifestContract(_ManifestCaseContract):
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


class ModelManifestSymbolContract(_ManifestCaseContract):
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


class ModelEnvironmentContract(_ManifestCaseContract):
    """Environment factory checks, run once per environment profile that the
    model spec allows."""

    def test_environment_factory_builds_model_environment(
        self, atomforge_environment_profile
    ):
        env_spec = self._build_environment_spec(atomforge_environment_profile)

        assert isinstance(env_spec, EnvironmentSpec)

    def test_environment_factory_is_deterministic_for_model_spec(
        self, atomforge_environment_profile
    ):
        first = self._build_environment_spec(atomforge_environment_profile)
        second = self._build_environment_spec(atomforge_environment_profile)

        assert second == first

    def test_environment_provider_requirements_include_entry_point_package(
        self, atomforge_environment_profile
    ):
        env_spec = self._build_environment_spec(atomforge_environment_profile)
        expected = normalize_distribution_name(self.case.entry_point_package)
        provider_requirements = {
            normalize_distribution_name(requirement)
            for requirement in env_spec.provider_requirements
        }

        assert expected in provider_requirements

    def test_environment_requirements_are_declared_in_dependency_summary(
        self, atomforge_environment_profile
    ):
        env_spec = self._build_environment_spec(atomforge_environment_profile)
        factory = self._environment_factory()
        declared = factory.dependency_summary.declared_requirements()

        assert frozenset(env_spec.requirements).issubset(declared)

    def test_environment_python_matches_dependency_summary(
        self, atomforge_environment_profile
    ):
        env_spec = self._build_environment_spec(atomforge_environment_profile)
        factory = self._environment_factory()
        expected_python = factory.dependency_summary.python

        if expected_python is not None:
            assert env_spec.python == expected_python

    def test_environment_channels_include_dependency_summary_channels(
        self, atomforge_environment_profile
    ):
        env_spec = self._build_environment_spec(atomforge_environment_profile)
        factory = self._environment_factory()
        expected_channels = set(factory.dependency_summary.channels)

        assert expected_channels.issubset(set(env_spec.channels))


def default_environment_provider(tmp_path):
    from atomforge.env.uv import UVEnvironmentProvider
    from atomforge.settings.settings import AtomforgeSettings

    settings = AtomforgeSettings()
    if settings.env_provider_kind == "uv":
        return UVEnvironmentProvider(search_path=(tmp_path,), install_path=tmp_path)

    raise AssertionError(
        f"Unsupported environment provider: {settings.env_provider_kind}"
    )


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


class ModelEnvironmentResolutionContract(_ManifestCaseContract):
    @pytest.mark.atomforge_environment
    def test_environment_resolves_with_default_provider(
        self, tmp_path, atomforge_environment_profile
    ):
        provider = default_environment_provider(tmp_path)
        env_spec = self._build_environment_spec(atomforge_environment_profile)

        result = provider.resolve_environment(env_spec)

        assert result.success, format_environment_resolution_failure(result)


class ModelSpecContract(_ManifestCaseContract):
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

    def test_model_spec_round_trips_through_json(self):
        model_spec = self._build_model_spec()
        spec_cls = type(model_spec)

        try:
            restored = spec_cls.model_validate_json(model_spec.model_dump_json())
        except ValidationError as exc:
            raise AssertionError(
                f"{spec_cls.__name__} does not survive a JSON round trip, which "
                f"is how specs reach the worker:\n{exc}"
            ) from exc

        assert restored == model_spec

    def test_model_spec_defaults_to_tested_environment_profile(self):
        model_spec = self._build_model_spec()

        assert model_spec.environment_profile == "tested"
        assert model_spec.model_dump()["environment_profile"] == "tested"
        assert "environment_profile" not in model_spec.scientific_payload()

    def test_model_spec_rejects_unknown_environment_profile(self):
        registration, _ = self._convert_manifest()
        model_spec = build_model_spec(self.case, registration)
        payload = model_spec.model_dump()
        payload["environment_profile"] = "unsupported"

        with pytest.raises(ValidationError):
            registration.model_spec.model_validate(payload)


class ModelRegistryContract(_ManifestCaseContract):
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


class _RuntimeContract(_ManifestCaseContract):
    """Helpers for contracts that execute the model through the backend.

    Runtime tests are marked on the methods, not the class: pytest collects
    class marks through the MRO, so a class mark would gate every test of a
    bundle that inherits the contract.
    """

    def _supported_properties(self) -> frozenset[Property]:
        registration, _ = self._convert_manifest()
        return registration.load_supported_properties()

    def _require(self, *properties: Property) -> None:
        missing = [p.value for p in properties if p not in self._supported_properties()]
        if missing:
            pytest.skip(
                f"{self.case.manifest.kind} does not declare {', '.join(missing)}"
            )

    def _runtime_structure(self) -> StructureData:
        if self.case.runtime_structure is not None:
            return self.case.runtime_structure
        return default_runtime_structure()

    def _structure_for(self, prop: Property) -> StructureData:
        structure = self._runtime_structure()
        if prop is Property.STRESS and not any(structure.pbc):
            from atomforge_testing.structures import periodic_bulk

            return periodic_bulk()
        return structure

    def _physics_structure(self, name: str) -> StructureData:
        if self.case.physics_structures is None:
            from atomforge_testing.structures import reference_structures

            structures = reference_structures()
        else:
            structures = self.case.physics_structures
        if name not in structures:
            pytest.skip(f"the case has no {name} physics structure")
        return structures[name]

    def _runtime_exec_resources(self) -> ExecutionResources:
        if self.case.runtime_exec_resources is not None:
            return self.case.runtime_exec_resources
        return default_runtime_exec_resources()

    def _execute_single_point(
        self,
        backend,
        properties: frozenset[Property],
        structure: StructureData,
        resources: ExecutionResources,
        environment_profile: str | None = None,
    ):
        if self.case.runtime_skip_reason is not None:
            pytest.skip(self.case.runtime_skip_reason)

        from atomforge_builtins.task.single_point import SinglePoint

        task = SinglePoint(structure=structure, properties=properties)
        model = self._build_model_spec(environment_profile)
        return backend.execute(task, model=model, exec_resources=resources)


class ModelSinglePointRuntimeContract(_RuntimeContract):
    """Runs the model through the backend: every declared property, and every
    declared resource combination with strict resources."""

    @pytest.mark.atomforge_runtime
    def test_declared_property_is_returned(
        self,
        atomforge_backend,
        atomforge_environment_profile,
        atomforge_declared_property,
    ):
        prop = atomforge_declared_property
        structure = self._structure_for(prop)

        result = self._execute_single_point(
            atomforge_backend,
            frozenset({prop}),
            structure,
            self._runtime_exec_resources(),
            atomforge_environment_profile,
        )

        PROPERTY_CHECKS[prop](result, structure)

    @pytest.mark.atomforge_runtime
    def test_declared_resources_execute_strictly(
        self,
        atomforge_backend,
        atomforge_environment_profile,
        atomforge_declared_resources,
    ):
        registration, _ = self._convert_manifest()
        supported = registration.load_supported_properties()
        if Property.ENERGY in supported:
            prop = Property.ENERGY
        else:
            prop = next(p for p in Property if p in supported)
        structure = self._structure_for(prop)

        result = self._execute_single_point(
            atomforge_backend,
            frozenset({prop}),
            structure,
            atomforge_declared_resources,
            atomforge_environment_profile,
        )

        PROPERTY_CHECKS[prop](result, structure)


# Rigid motions used by the invariance checks; arbitrary but fixed.
TRANSLATION = (0.37, -0.21, 0.13)
ROTATION_AXIS = (1.0, 1.0, 1.0)
ROTATION_DEGREES = 37.0


ALL_STRUCTURES = pytest.mark.parametrize("structure_name", PHYSICS_STRUCTURE_NAMES)
MOLECULE = pytest.mark.parametrize("structure_name", ["molecule"])
PERIODIC = pytest.mark.parametrize("structure_name", ["slab", "bulk"])


class ModelPhysicsContract(_RuntimeContract):
    """Model-independent physics checks on runtime results, compared with the
    tolerances of the precision the model ran at
    (atomforge_testing.physics). Each check runs on the reference structures
    it applies to, or on the case's ``physics_structures``."""

    def _require_physics(self, *properties: str) -> None:
        missing = self.case.physics.missing(*properties)
        if missing:
            declared = ", ".join(f"{name}=False" for name in missing)
            pytest.skip(f"the case declares ModelPhysics({declared})")

    def _tolerances(self, resources: ExecutionResources) -> Tolerances:
        return physics.tolerances_for(resources.precision, self.case.tolerances)

    def _run(self, backend, profile, structure, properties, resources=None):
        return self._execute_single_point(
            backend,
            frozenset(properties),
            structure,
            resources or self._runtime_exec_resources(),
            profile,
        )

    def _finite_difference_resources(self) -> ExecutionResources:
        resources = self._runtime_exec_resources()
        capabilities = self.case.manifest.resource_capabilities.load_symbol()
        if "f64" in (capabilities.precision or []):
            return resources.model_copy(update={"precision": "f64"})
        return resources

    @pytest.mark.atomforge_runtime
    @ALL_STRUCTURES
    def test_energy_is_invariant_under_translation(
        self, atomforge_backend, atomforge_environment_profile, structure_name
    ):
        self._require_physics("translation_invariant")
        self._require(Property.ENERGY)
        structure = self._physics_structure(structure_name)
        tolerance = self._tolerances(self._runtime_exec_resources())

        before = self._run(
            atomforge_backend,
            atomforge_environment_profile,
            structure,
            {Property.ENERGY},
        )
        after = self._run(
            atomforge_backend,
            atomforge_environment_profile,
            physics.translated(structure, TRANSLATION),
            {Property.ENERGY},
        )

        deviation = physics.energy_per_atom_difference(
            before.energy, after.energy, len(structure.numbers)
        )
        assert deviation <= tolerance.energy_per_atom, (
            f"energy of the {structure_name} changed by {deviation:.3g} "
            f"eV/atom under a rigid translation "
            f"(tolerance {tolerance.energy_per_atom:.3g})"
        )

    @pytest.mark.atomforge_runtime
    @MOLECULE
    def test_energy_is_invariant_under_rotation(
        self, atomforge_backend, atomforge_environment_profile, structure_name
    ):
        self._require_physics("rotation_invariant")
        self._require(Property.ENERGY)
        structure = self._physics_structure(structure_name)
        tolerance = self._tolerances(self._runtime_exec_resources())

        before = self._run(
            atomforge_backend,
            atomforge_environment_profile,
            structure,
            {Property.ENERGY},
        )
        after = self._run(
            atomforge_backend,
            atomforge_environment_profile,
            physics.rotated(structure, ROTATION_AXIS, ROTATION_DEGREES),
            {Property.ENERGY},
        )

        deviation = physics.energy_per_atom_difference(
            before.energy, after.energy, len(structure.numbers)
        )
        assert deviation <= tolerance.energy_per_atom, (
            f"energy of the molecule changed by {deviation:.3g} eV/atom under "
            f"a rigid rotation (tolerance {tolerance.energy_per_atom:.3g})"
        )

    @pytest.mark.atomforge_runtime
    @MOLECULE
    def test_forces_sum_to_zero(
        self, atomforge_backend, atomforge_environment_profile, structure_name
    ):
        self._require_physics("conservative_forces", "translation_invariant")
        self._require(Property.FORCES)
        structure = self._physics_structure(structure_name)
        tolerance = self._tolerances(self._runtime_exec_resources())

        result = self._run(
            atomforge_backend,
            atomforge_environment_profile,
            structure,
            {Property.FORCES},
        )

        deviation = physics.net_force_per_atom(result.forces)
        assert deviation <= tolerance.forces, (
            f"net force on the molecule is {deviation:.3g} eV/Å per atom "
            f"(tolerance {tolerance.forces:.3g})"
        )

    @pytest.mark.atomforge_runtime
    @ALL_STRUCTURES
    def test_forces_match_energy_gradient(
        self, atomforge_backend, atomforge_environment_profile, structure_name
    ):
        self._require_physics("conservative_forces")
        self._require(Property.ENERGY, Property.FORCES)
        structure = self._physics_structure(structure_name)
        resources = self._finite_difference_resources()
        tolerance = self._tolerances(resources)
        step = tolerance.finite_difference_step

        forces = self._run(
            atomforge_backend,
            atomforge_environment_profile,
            structure,
            {Property.FORCES},
            resources,
        ).forces
        coordinates = physics.largest_force_coordinates(forces)
        largest = abs(forces[coordinates[0][0]][coordinates[0][1]])
        needed = physics.INFORMATIVE_FACTOR * tolerance.finite_difference
        assert largest >= needed, (
            f"uninformative: the largest force component on the "
            f"{structure_name} is {largest:.3g} eV/Å, too small against the "
            f"finite-difference tolerance {tolerance.finite_difference:.3g} to "
            f"tell a wrong sign (needs {needed:.3g}); give the case a "
            f"physics structure with larger forces"
        )

        errors = {}
        for atom, axis in coordinates:
            plus, minus = (
                self._run(
                    atomforge_backend,
                    atomforge_environment_profile,
                    physics.displaced(structure, atom, axis, sign * step),
                    {Property.ENERGY},
                    resources,
                ).energy
                for sign in (1, -1)
            )
            expected = physics.central_difference_force(plus, minus, step)
            errors[(atom, "xyz"[axis])] = abs(forces[atom][axis] - expected)

        worst = max(errors, key=errors.get)
        assert errors[worst] <= tolerance.finite_difference, (
            f"force on atom {worst[0]} of the {structure_name} along "
            f"{worst[1]} differs from minus the energy gradient (central "
            f"difference, step {step} Å, {resources.precision}) by "
            f"{errors[worst]:.3g} eV/Å "
            f"(tolerance {tolerance.finite_difference:.3g})"
        )

    @pytest.mark.atomforge_runtime
    @ALL_STRUCTURES
    def test_repeated_request_gives_same_result(
        self, atomforge_backend, atomforge_environment_profile, structure_name
    ):
        self._require(Property.ENERGY)
        properties = {Property.ENERGY, Property.FORCES} & self._supported_properties()
        structure = self._physics_structure(structure_name)
        tolerance = self._tolerances(self._runtime_exec_resources())

        first = self._run(
            atomforge_backend, atomforge_environment_profile, structure, properties
        )
        second = self._run(
            atomforge_backend, atomforge_environment_profile, structure, properties
        )

        energy_deviation = physics.energy_per_atom_difference(
            first.energy, second.energy, len(structure.numbers)
        )
        assert energy_deviation <= tolerance.energy_per_atom, (
            f"two identical requests on the {structure_name} differ by "
            f"{energy_deviation:.3g} eV/atom "
            f"(tolerance {tolerance.energy_per_atom:.3g})"
        )
        if Property.FORCES in properties:
            force_deviation = physics.max_abs_difference(first.forces, second.forces)
            assert force_deviation <= tolerance.forces, (
                f"two identical requests on the {structure_name} differ by "
                f"{force_deviation:.3g} eV/Å in the forces "
                f"(tolerance {tolerance.forces:.3g})"
            )

    @pytest.mark.atomforge_runtime
    @ALL_STRUCTURES
    def test_per_atom_energies_sum_to_energy(
        self, atomforge_backend, atomforge_environment_profile, structure_name
    ):
        self._require(Property.ENERGY, Property.ENERGIES)
        structure = self._physics_structure(structure_name)
        tolerance = self._tolerances(self._runtime_exec_resources())

        result = self._run(
            atomforge_backend,
            atomforge_environment_profile,
            structure,
            {Property.ENERGY, Property.ENERGIES},
        )

        deviation = physics.per_atom_energies_deviation(result.energies, result.energy)
        assert deviation <= tolerance.energy_per_atom, (
            f"per-atom energies of the {structure_name} sum to the energy only "
            f"within {deviation:.3g} eV/atom "
            f"(tolerance {tolerance.energy_per_atom:.3g})"
        )

    @pytest.mark.atomforge_runtime
    @PERIODIC
    def test_stress_is_symmetric(
        self, atomforge_backend, atomforge_environment_profile, structure_name
    ):
        self._require_physics("conservative_forces", "rotation_invariant")
        self._require(Property.STRESS)
        structure = self._physics_structure(structure_name)
        tolerance = self._tolerances(self._runtime_exec_resources())

        result = self._run(
            atomforge_backend,
            atomforge_environment_profile,
            structure,
            {Property.STRESS},
        )

        deviation = physics.stress_asymmetry(result.stress)
        assert deviation <= tolerance.stress, (
            f"stress of the {structure_name} is asymmetric by "
            f"{deviation:.3g} eV/Å³ (tolerance {tolerance.stress:.3g})"
        )


class ModelReferenceContract(_RuntimeContract):
    """Compares results on the physics structures with references stored next
    to the plugin's tests (pytest-regressions' ``ndarrays_regression``; needs
    ``atomforge-testing[regression]``).

    One reference per structure, named ``<kind>-<structure>.npz``. The
    ``tested`` profile's test records it when it is missing, or under
    ``--force-regen`` or ``--regen-all``: on CPU, at the highest declared
    precision. Every profile compares its result, at the case's runtime
    resources, with the same reference and the reference tolerances.
    """

    def _reference_tolerances(self) -> ReferenceTolerances:
        if self.case.reference_tolerances is not None:
            return self.case.reference_tolerances
        return physics.REFERENCE_TOLERANCES

    @pytest.mark.atomforge_runtime
    @ALL_STRUCTURES
    def test_matches_reference(
        self, request, atomforge_backend, atomforge_environment_profile, structure_name
    ):
        from atomforge_testing import reference

        self._require(Property.ENERGY)
        structure = self._physics_structure(structure_name)
        regression = reference.ndarrays_regression(request)
        name = reference.reference_name(self.case.manifest.kind, structure_name)
        path = request.getfixturevalue("original_datadir") / f"{name}.npz"
        regenerating = request.config.getoption(
            "force_regen"
        ) or request.config.getoption("regen_all")
        records = atomforge_environment_profile == reference.RECORDING_PROFILE

        if not records:
            if regenerating:
                pytest.skip(
                    "references are being regenerated; only the "
                    f"{reference.RECORDING_PROFILE} profile records them"
                )
            if not path.is_file():
                pytest.fail(
                    f"no reference {path}; run test_matches_reference"
                    f"[{reference.RECORDING_PROFILE}-{structure_name}] to record it",
                    pytrace=False,
                )

        supported = self._supported_properties()
        properties = {Property.ENERGY}
        if Property.FORCES in supported:
            properties.add(Property.FORCES)
        if Property.STRESS in supported and any(structure.pbc):
            properties.add(Property.STRESS)

        if records and (regenerating or not path.is_file()):
            capabilities = self.case.manifest.resource_capabilities.load_symbol()
            resources = reference.recording_resources(capabilities)
            profile = reference.RECORDING_PROFILE
        else:
            resources = self._runtime_exec_resources()
            profile = atomforge_environment_profile

        result = self._execute_single_point(
            atomforge_backend, frozenset(properties), structure, resources, profile
        )

        regression.check(
            reference.arrays(result, len(structure.numbers)),
            basename=name,
            tolerances=reference.tolerances(self._reference_tolerances()),
        )


class ModelPluginContract(
    ModelManifestContract,
    ModelManifestSymbolContract,
    ModelSpecContract,
    ModelRegistryContract,
    ModelEnvironmentContract,
    ModelEnvironmentResolutionContract,
    ModelSinglePointRuntimeContract,
    ModelPhysicsContract,
    ModelReferenceContract,
):
    """Every model plugin contract. Subclass it once per model and set
    ``manifest_case``; the environment and runtime contracts run only with
    ``--atomforge-environment`` and ``--atomforge-runtime``."""
