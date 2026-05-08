from pathlib import Path
import sys

import pytest

from atomforge_core.model.result import ModelResult
from atomforge_core.registry.model_manifest import ModelManifest
from atomforge_core.registry.symbol_path import SymbolPath
from atomforge_core.structure import StructureData
from atomforge_runtime.registry.model.model_registration import ModelRegistration
from atomforge_testing import structures
from atomforge_testing import (
    ModelEnvironmentContract,
    ModelEnvironmentResolutionContract,
    ModelManifestCase,
    ModelManifestContract,
    ModelRegistryContract,
    ModelManifestSymbolContract,
    ModelSpecContract,
    ModelSinglePointRuntimeContract,
)
import atomforge_testing.model_manifest as model_manifest_contracts
from atomforge_testing.model_manifest import (
    assert_energy_result,
    assert_forces_result,
    skip_environment_resolution_contract_unless_enabled,
    skip_runtime_contract_unless_enabled,
)


TESTS_PATH = Path(__file__).resolve().parent

if str(TESTS_PATH) not in sys.path:
    sys.path.insert(0, str(TESTS_PATH))


def manifest_factory(
    distribution="fake-plugin",
    model_spec="testing_fakes:FakeModel",
    executor_cls="testing_fakes:FakeModelExecutor",
    supported_properties="testing_fakes:FakeSupportedProperties",
    environment_factory_cls="testing_fakes:FakeEnvironmentFactory",
    metadata="testing_fakes:FakeMetadata",
    resource_capabilities="testing_fakes:FakeResourceCapabilities",
    probe=None,
    task_overrides=None,
) -> ModelManifest:
    if task_overrides is None:
        task_overrides = {}
    return ModelManifest(
        kind="fake-model",
        model_spec=model_spec,
        executor_cls=executor_cls,
        supported_properties=supported_properties,
        environment_factory_cls=environment_factory_cls,
        metadata=metadata,
        resource_capabilities=resource_capabilities,
        distribution=distribution,
        probe=probe,
        task_overrides=task_overrides,
    )


def broken_environment_manifest_factory(distribution="fake-plugin") -> ModelManifest:
    return manifest_factory(
        distribution=distribution,
        environment_factory_cls="testing_fakes:BrokenEnvironmentFactory",
    )


def write_pyproject(tmp_path, entry_points: dict[str, str]) -> Path:
    lines = [
        "[project]",
        'name = "fake-plugin"',
        "",
        "[project.entry-points.'atomforge.model']",
    ]
    lines.extend(f'{name} = "{target}"' for name, target in entry_points.items())
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("\n".join(lines))
    return pyproject


def build_case(tmp_path, **overrides) -> ModelManifestCase:
    target = "testing_fakes:fake_manifest"
    pyproject_path = overrides.pop("pyproject_path", None)
    if pyproject_path is None:
        pyproject_path = write_pyproject(tmp_path, {"fake": target})
    values = {
        "manifest": manifest_factory(),
        "entry_point_name": "fake",
        "entry_point_package": "fake-plugin",
        "pyproject_path": pyproject_path,
        "expected_entry_point_target": target,
    }
    values.update(overrides)
    return ModelManifestCase(**values)


class FakeManifestContract(ModelManifestContract):
    pass


class FakeModelManifestSymbolContract(ModelManifestSymbolContract):
    pass


class FakeModelEnvironmentContract(ModelEnvironmentContract):
    pass


class FakeModelEnvironmentResolutionContract(ModelEnvironmentResolutionContract):
    pass


class FakeModelSpecContract(ModelSpecContract):
    pass


class FakeModelRegistryContract(ModelRegistryContract):
    pass


class FakeRuntimeContract(ModelSinglePointRuntimeContract):
    pass


class FakeRegistry:
    def __init__(self, registrations: dict[str, ModelRegistration]):
        self._registrations = registrations

    def get(self, kind: str):
        return self._registrations[kind]


class FakeEnvironmentProvider:
    def __init__(self, result):
        self.result = result
        self.resolved_specs = []

    def resolve_environment(self, spec):
        self.resolved_specs.append(spec)
        return self.result


class FakeResolutionResult:
    def __init__(
        self,
        *,
        success=True,
        provider="fake",
        command=("fake", "resolve"),
        project_path=Path("/tmp/fake-project"),
        message=None,
        stdout="",
        stderr="",
    ):
        self.provider = provider
        self.success = success
        self.command = command
        self.project_path = project_path
        self.message = message
        self.stdout = stdout
        self.stderr = stderr


def registration_factory(
    *,
    kind="fake-model",
    model_spec=None,
    source=None,
) -> ModelRegistration:
    if model_spec is None:
        from testing_fakes import FakeModel

        model_spec = FakeModel
    if source is None:
        source = ["fake-plugin"]

    return ModelRegistration(
        kind=kind,
        model_spec=model_spec,
        metadata_path=SymbolPath("testing_fakes:FakeMetadata"),
        executor_class_path=SymbolPath("testing_fakes:FakeModelExecutor"),
        supported_properties_path=SymbolPath("testing_fakes:FakeSupportedProperties"),
        environment_factory_path=SymbolPath("testing_fakes:FakeEnvironmentFactory"),
        resource_capabilities_path=SymbolPath("testing_fakes:FakeResourceCapabilities"),
        source=source,
    )


def patch_default_model_registry(monkeypatch, registry: FakeRegistry) -> None:
    monkeypatch.setattr(
        model_manifest_contracts.ModelRegistry,
        "default",
        classmethod(lambda cls: registry),
    )


def test_entry_point_parsing_succeeds_for_matching_target(tmp_path):
    contract = FakeManifestContract()
    contract.manifest_case = build_case(tmp_path)

    contract.test_pyproject_entry_point_targets_manifest()


def test_entry_point_parsing_fails_for_missing_entry_point(tmp_path):
    contract = FakeManifestContract()
    contract.manifest_case = build_case(
        tmp_path,
        pyproject_path=write_pyproject(tmp_path, {"other": "testing_fakes:fake_manifest"}),
    )

    with pytest.raises(AssertionError):
        contract.test_pyproject_entry_point_targets_manifest()


def test_entry_point_parsing_fails_for_mismatched_target(tmp_path):
    contract = FakeManifestContract()
    contract.manifest_case = build_case(
        tmp_path,
        pyproject_path=write_pyproject(tmp_path, {"fake": "testing_fakes:other"}),
    )

    with pytest.raises(AssertionError):
        contract.test_pyproject_entry_point_targets_manifest()


def test_conversion_and_strict_validation_use_runtime_registration(tmp_path):
    contract = FakeManifestContract()
    contract.manifest_case = build_case(tmp_path)

    contract.test_manifest_converts_to_model_registration()
    contract.test_registration_validate_strict_loads_manifest_paths()


def test_symbol_contract_accepts_valid_manifest_symbols(tmp_path):
    contract = FakeModelManifestSymbolContract()
    contract.manifest_case = build_case(
        tmp_path,
        manifest=manifest_factory(
            probe="testing_fakes:fake_probe",
            task_overrides={
                "fake_task": "testing_fakes:FakeTaskOverrideExecutor",
            },
        ),
    )

    contract.test_model_spec_symbol_is_model_spec_subclass()
    contract.test_executor_symbol_is_model_executor_subclass()
    contract.test_supported_properties_symbol_is_property_set()
    contract.test_environment_factory_symbol_is_environment_factory_subclass()
    contract.test_metadata_symbol_is_model_metadata()
    contract.test_resource_capabilities_symbol_is_resource_capabilities()
    contract.test_optional_probe_symbol_is_callable_when_present()
    contract.test_task_override_symbols_are_task_executor_subclasses()


@pytest.mark.parametrize(
    ("manifest_kwargs", "contract_method_name"),
    [
        (
            {"model_spec": "testing_fakes:FakeMetadata"},
            "test_model_spec_symbol_is_model_spec_subclass",
        ),
        (
            {"executor_cls": "testing_fakes:FakeMetadata"},
            "test_executor_symbol_is_model_executor_subclass",
        ),
        (
            {"supported_properties": "testing_fakes:FakeMetadata"},
            "test_supported_properties_symbol_is_property_set",
        ),
        (
            {"environment_factory_cls": "testing_fakes:FakeModel"},
            "test_environment_factory_symbol_is_environment_factory_subclass",
        ),
        (
            {"metadata": "testing_fakes:FakeModel"},
            "test_metadata_symbol_is_model_metadata",
        ),
        (
            {"resource_capabilities": "testing_fakes:FakeMetadata"},
            "test_resource_capabilities_symbol_is_resource_capabilities",
        ),
        (
            {"probe": "testing_fakes:FakeModel"},
            "test_optional_probe_symbol_is_callable_when_present",
        ),
        (
            {
                "task_overrides": {
                    "fake_task": "testing_fakes:FakeModel",
                }
            },
            "test_task_override_symbols_are_task_executor_subclasses",
        ),
    ],
)
def test_symbol_contract_fails_for_wrong_symbol_categories(
    tmp_path,
    manifest_kwargs,
    contract_method_name,
):
    contract = FakeModelManifestSymbolContract()
    contract.manifest_case = build_case(
        tmp_path,
        manifest=manifest_factory(**manifest_kwargs),
    )

    with pytest.raises(AssertionError):
        getattr(contract, contract_method_name)()


def test_environment_contract_builds_model_environment(tmp_path):
    contract = FakeModelEnvironmentContract()
    contract.manifest_case = build_case(tmp_path)

    contract.test_environment_factory_builds_model_environment()


def test_environment_contract_is_deterministic_for_model_spec(tmp_path):
    contract = FakeModelEnvironmentContract()
    contract.manifest_case = build_case(tmp_path)

    contract.test_environment_factory_is_deterministic_for_model_spec()


def test_environment_contract_checks_provider_requirements(tmp_path):
    contract = FakeModelEnvironmentContract()
    contract.manifest_case = build_case(tmp_path)

    contract.test_environment_provider_requirements_include_entry_point_package()


def test_environment_contract_checks_dependency_summary_details(tmp_path):
    contract = FakeModelEnvironmentContract()
    contract.manifest_case = build_case(tmp_path)

    contract.test_environment_requirements_are_declared_in_dependency_summary()
    contract.test_environment_python_matches_dependency_summary()
    contract.test_environment_channels_include_dependency_summary_channels()


def test_environment_contract_fails_on_undeclared_requirements(tmp_path):
    contract = FakeModelEnvironmentContract()
    contract.manifest_case = build_case(
        tmp_path,
        manifest=broken_environment_manifest_factory(),
    )

    with pytest.raises(ValueError):
        contract.test_environment_factory_builds_model_environment()


def test_environment_contract_fails_on_non_deterministic_factory(tmp_path):
    contract = FakeModelEnvironmentContract()
    contract.manifest_case = build_case(
        tmp_path,
        manifest=manifest_factory(
            environment_factory_cls="testing_fakes:NonDeterministicEnvironmentFactory",
        ),
    )

    with pytest.raises(AssertionError):
        contract.test_environment_factory_is_deterministic_for_model_spec()


class FakeRequest:
    class Config:
        class Option:
            markexpr = "atomforge_environment"

        option = Option()

    config = Config()


class FakeUnmarkedRequest:
    class Config:
        class Option:
            markexpr = ""

        option = Option()

    config = Config()


def test_environment_resolution_contract_uses_provider_resolution(
    tmp_path,
    monkeypatch,
):
    result = FakeResolutionResult(success=True)
    provider = FakeEnvironmentProvider(result)
    contract = FakeModelEnvironmentResolutionContract()
    contract.manifest_case = build_case(tmp_path)

    monkeypatch.setattr(
        model_manifest_contracts,
        "default_environment_provider",
        lambda provider_tmp_path: provider,
    )

    contract.test_environment_resolves_with_default_provider(FakeRequest(), tmp_path)

    assert len(provider.resolved_specs) == 1
    assert provider.resolved_specs[0].name == "fake-env"


def test_environment_resolution_contract_fails_with_diagnostics(
    tmp_path,
    monkeypatch,
):
    result = FakeResolutionResult(
        success=False,
        message="failed",
        stdout="resolver stdout",
        stderr="resolver stderr",
    )
    provider = FakeEnvironmentProvider(result)
    contract = FakeModelEnvironmentResolutionContract()
    contract.manifest_case = build_case(tmp_path)

    monkeypatch.setattr(
        model_manifest_contracts,
        "default_environment_provider",
        lambda provider_tmp_path: provider,
    )

    with pytest.raises(AssertionError) as exc_info:
        contract.test_environment_resolves_with_default_provider(
            FakeRequest(),
            tmp_path,
        )

    message = str(exc_info.value)
    assert "Environment resolution failed." in message
    assert "provider: fake" in message
    assert "resolver stdout" in message
    assert "resolver stderr" in message


def test_environment_resolution_contract_skips_without_marker():
    with pytest.raises(pytest.skip.Exception):
        skip_environment_resolution_contract_unless_enabled(FakeUnmarkedRequest())


def test_model_spec_factory_returns_registered_model_spec(tmp_path):
    contract = FakeModelSpecContract()
    contract.manifest_case = build_case(
        tmp_path,
        manifest=manifest_factory(model_spec="testing_fakes:RequiredFakeModel"),
        model_spec_factory=lambda model_cls: model_cls(variant="small"),
    )

    contract.test_model_spec_factory_returns_registered_model_spec()


def test_model_spec_factory_wrong_return_type_fails(tmp_path):
    contract = FakeModelSpecContract()
    contract.manifest_case = build_case(
        tmp_path,
        model_spec_factory=lambda model_cls: object(),
    )

    with pytest.raises(AssertionError):
        contract.test_model_spec_factory_returns_registered_model_spec()


def test_model_spec_kind_mismatch_fails(tmp_path):
    contract = FakeModelSpecContract()
    contract.manifest_case = build_case(
        tmp_path,
        manifest=manifest_factory(model_spec="testing_fakes:MismatchedKindFakeModel"),
    )

    with pytest.raises(AssertionError):
        contract.test_model_spec_kind_matches_manifest_kind()


def test_model_spec_round_trips_through_model_dump(tmp_path):
    contract = FakeModelSpecContract()
    contract.manifest_case = build_case(
        tmp_path,
        manifest=manifest_factory(model_spec="testing_fakes:RequiredFakeModel"),
        model_spec_factory=lambda model_cls: model_cls(variant="small"),
    )

    contract.test_model_spec_round_trips_through_model_dump()


def test_registry_contract_discovers_model(tmp_path, monkeypatch):
    contract = FakeModelRegistryContract()
    contract.manifest_case = build_case(tmp_path)
    patch_default_model_registry(
        monkeypatch,
        FakeRegistry({"fake-model": registration_factory()}),
    )

    contract.test_model_is_discoverable_by_default_registry()
    contract.test_discovered_registration_kind_matches_manifest()
    contract.test_discovered_registration_source_includes_entry_point_package()
    contract.test_discovered_registration_model_spec_matches_manifest_path()


def test_registry_contract_fails_for_unknown_model_kind(tmp_path, monkeypatch):
    contract = FakeModelRegistryContract()
    contract.manifest_case = build_case(tmp_path)
    patch_default_model_registry(monkeypatch, FakeRegistry({}))

    with pytest.raises(KeyError):
        contract.test_model_is_discoverable_by_default_registry()


def test_registry_contract_fails_for_wrong_source(tmp_path, monkeypatch):
    contract = FakeModelRegistryContract()
    contract.manifest_case = build_case(tmp_path)
    patch_default_model_registry(
        monkeypatch,
        FakeRegistry(
            {"fake-model": registration_factory(source=["different-plugin"])}
        ),
    )

    with pytest.raises(AssertionError):
        contract.test_discovered_registration_source_includes_entry_point_package()


def test_registry_contract_fails_for_model_spec_mismatch(tmp_path, monkeypatch):
    from testing_fakes import RequiredFakeModel

    contract = FakeModelRegistryContract()
    contract.manifest_case = build_case(tmp_path)
    patch_default_model_registry(
        monkeypatch,
        FakeRegistry(
            {
                "fake-model": registration_factory(
                    model_spec=RequiredFakeModel,
                )
            }
        ),
    )

    with pytest.raises(AssertionError):
        contract.test_discovered_registration_model_spec_matches_manifest_path()


def test_runtime_gate_skips_when_environment_variable_is_unset(monkeypatch):
    monkeypatch.delenv("ATOMFORGE_RUN_RUNTIME_TESTS", raising=False)

    with pytest.raises(pytest.skip.Exception):
        skip_runtime_contract_unless_enabled()


def test_runtime_gate_does_not_skip_when_environment_variable_is_set(monkeypatch):
    monkeypatch.setenv("ATOMFORGE_RUN_RUNTIME_TESTS", "1")

    skip_runtime_contract_unless_enabled()


def test_energy_result_accepts_numeric_energy():
    assert_energy_result(ModelResult(energy=1))
    assert_energy_result(ModelResult(energy=1.0))


def test_energy_result_rejects_missing_energy():
    with pytest.raises(AssertionError):
        assert_energy_result(ModelResult(energy=None))


def test_forces_result_accepts_one_three_vector_per_atom():
    structure = StructureData(
        positions=[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
        cell=[[10.0, 0.0, 0.0], [0.0, 10.0, 0.0], [0.0, 0.0, 10.0]],
        numbers=[1, 8],
        pbc=[False, False, False],
    )
    result = ModelResult(
        forces=[
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
        ]
    )

    assert_forces_result(result, structure)


def test_forces_result_rejects_wrong_shape():
    structure = StructureData(
        positions=[[0.0, 0.0, 0.0]],
        cell=[[10.0, 0.0, 0.0], [0.0, 10.0, 0.0], [0.0, 0.0, 10.0]],
        numbers=[1],
        pbc=[False, False, False],
    )

    with pytest.raises(AssertionError):
        assert_forces_result(ModelResult(forces=[[0.0, 0.0]]), structure)


@pytest.mark.parametrize(
    "structure_factory",
    [
        structures.small_molecule,
        structures.periodic_bulk,
        structures.isolated_atom,
    ],
)
def test_reference_structure_helpers_return_valid_structure_data(structure_factory):
    structure = structure_factory()

    assert isinstance(structure, StructureData)
    assert len(structure.positions) == len(structure.numbers)
    assert len(structure.cell) == 3
    assert len(structure.pbc) == 3


def test_reference_structure_helpers_return_fresh_instances():
    first = structures.small_molecule()
    second = structures.small_molecule()

    assert first is not second
    assert first == second
