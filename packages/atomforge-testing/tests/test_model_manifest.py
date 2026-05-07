from pathlib import Path
import sys

import pytest

from atomforge_core.model.result import ModelResult
from atomforge_core.registry.model_manifest import ModelManifest
from atomforge_core.structure import StructureData
from atomforge_testing import (
    ModelManifestCase,
    ModelManifestContract,
    ModelSpecContract,
    ModelSinglePointRuntimeContract,
)
from atomforge_testing.model_manifest import (
    assert_energy_result,
    assert_forces_result,
    skip_runtime_contract_unless_enabled,
)


TESTS_PATH = Path(__file__).resolve().parent

if str(TESTS_PATH) not in sys.path:
    sys.path.insert(0, str(TESTS_PATH))


def manifest_factory(
    distribution="fake-plugin",
    model_spec="testing_fakes:FakeModel",
    environment_factory_cls="testing_fakes:FakeEnvironmentFactory",
) -> ModelManifest:
    return ModelManifest(
        kind="fake-model",
        model_spec=model_spec,
        executor_cls="testing_fakes:FakeModelExecutor",
        supported_properties="testing_fakes:FakeSupportedProperties",
        environment_factory_cls=environment_factory_cls,
        metadata="testing_fakes:FakeMetadata",
        resource_capabilities="testing_fakes:FakeResourceCapabilities",
        distribution=distribution,
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


class FakeModelSpecContract(ModelSpecContract):
    pass


class FakeRuntimeContract(ModelSinglePointRuntimeContract):
    pass


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


def test_environment_factory_contract_builds_model_environment(tmp_path):
    contract = FakeManifestContract()
    contract.manifest_case = build_case(tmp_path)

    contract.test_environment_factory_builds_default_model_environment()


def test_environment_factory_contract_fails_on_undeclared_requirements(tmp_path):
    contract = FakeManifestContract()
    contract.manifest_case = build_case(
        tmp_path,
        manifest=broken_environment_manifest_factory(),
    )

    with pytest.raises(ValueError):
        contract.test_environment_factory_builds_default_model_environment()


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
