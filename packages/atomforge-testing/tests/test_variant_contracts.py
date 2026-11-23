"""Acceptance tests for the atomforge-testing part of "Variants, settings and
local weights in the spec, design" in the engineering log.

- References are named `<kind>-<variant>-<structure>`.
- A case runs its default variant only, the variants it names, or every
  generated variant with `--atomforge-all-variants`.
- `ModelSpecContract` checks the generated variants and `variant_info`.
- `ModelLocalWeightsContract`, collected when the spec declares `weights`,
  checks that a variant's own parameters loaded from a file give the
  variant's results, and that a changed file is rejected.

Each test runs contracts in an inner pytest session, against a backend that
runs the fake executor in process.
"""

from pathlib import Path
import re
import sys

import pytest

TESTS_PATH = Path(__file__).resolve().parent

if str(TESTS_PATH) not in sys.path:
    sys.path.insert(0, str(TESTS_PATH))

import testing_fakes  # noqa: E402

PYPROJECT = """\
[project]
name = "fake-plugin"

[project.entry-points.'atomforge.model']
fake = "testing_fakes:fake_manifest"
"""

CASE_MODULE = """\
from pathlib import Path

from atomforge_core.registry.model_manifest import ModelManifest
from atomforge_core.resources.resource_models import ExecutionResources
from atomforge_testing import ModelManifestCase

import variant_fakes

PYPROJECT = Path(__file__).parent / "pyproject.toml"

CASE = ModelManifestCase(
    manifest=ModelManifest(
        kind="fake-model",
        model_spec="{model_spec}",
        executor_cls="variant_fakes:VariantSpringExecutor",
        supported_properties="{supported_properties}",
        environment_factory_cls="testing_fakes:FakeEnvironmentFactory",
        metadata="testing_fakes:FakeMetadata",
        resource_capabilities="{resource_capabilities}",
        distribution="fake-plugin",
        variant_info={variant_info},
    ),
    entry_point_name="fake",
    entry_point_package="fake-plugin",
    pyproject_path=PYPROJECT,
    expected_entry_point_target="testing_fakes:fake_manifest",
    runtime_exec_resources=ExecutionResources(accelerator="cpu", precision="f64"),
    {case_extra}
)
"""

CONFTEST = """\
import pytest

from fake_case import CASE
import variant_fakes


@pytest.fixture(scope="session")
def atomforge_backend():
    return variant_fakes.{backend}(CASE.manifest)
"""

TESTS = """\
from fake_case import CASE
from atomforge_testing import {contract}


class TestFake({contract}):
    manifest_case = CASE
"""

STRUCTURES = ("molecule", "slab", "bulk")


def write_project(
    pytester,
    *,
    contract,
    model_spec="variant_fakes:ThreeVariantModel",
    variant_info=None,
    case_extra="",
    backend="VerifyingInProcessBackend",
    supported_properties="testing_fakes:EnergyForcesStress",
    resource_capabilities="testing_fakes:F32F64Capabilities",
):
    pytester.makefile(".toml", pyproject=PYPROJECT)
    pytester.makepyfile(
        fake_case=CASE_MODULE.format(
            model_spec=model_spec,
            variant_info="None" if variant_info is None else repr(variant_info),
            case_extra=case_extra,
            supported_properties=supported_properties,
            resource_capabilities=resource_capabilities,
        )
    )
    pytester.makeconftest(CONFTEST.format(backend=backend))
    pytester.makepyfile(test_contracts=TESTS.format(contract=contract))
    pytester.syspathinsert()


OUTCOME = re.compile(r"::TestFake::(\w+)(\[[^\]]*\])? (PASSED|FAILED|SKIPPED|ERROR)")


def run(pytester, *args):
    """The inner session's result and the outcome of each test, by name and
    parameter id."""
    result = pytester.runpytest_inprocess("-v", *args)
    found = {}
    for line in result.outlines:
        match = OUTCOME.search(line)
        if match:
            found[match.group(1) + (match.group(2) or "")] = match.group(3)
    return result, found


def outcomes(found):
    return set(found.values())


@pytest.fixture(autouse=True)
def reset_recorders():
    testing_fakes.InProcessBackend.instances = []


def requested_models():
    return [
        model
        for backend in testing_fakes.InProcessBackend.instances
        for _, model, _ in backend.requests
        if model is not None
    ]


def requested_variants():
    return {model.variant_name for model in requested_models()}


def reference_files(pytester):
    directory = pytester.path / "test_contracts"
    if not directory.exists():
        return set()
    return {path.name for path in directory.glob("*.npz")}


# References and the variants a case runs


def test_references_are_named_by_kind_variant_and_structure(pytester):
    write_project(
        pytester,
        contract="ModelReferenceContract",
        model_spec="testing_fakes:FakeModel",
    )

    run(pytester, "--atomforge-runtime")

    assert reference_files(pytester) == {
        f"fake-model-default-{structure}.npz" for structure in STRUCTURES
    }


def test_a_case_runs_its_default_variant_only(pytester):
    write_project(pytester, contract="ModelReferenceContract")

    run(pytester, "--atomforge-runtime")

    assert requested_variants() == {"a"}
    assert reference_files(pytester) == {
        f"fake-model-a-{structure}.npz" for structure in STRUCTURES
    }


def test_all_variants_runs_every_generated_variant(pytester):
    write_project(pytester, contract="ModelReferenceContract")

    run(pytester, "--atomforge-runtime", "--atomforge-all-variants")

    assert requested_variants() == {"a", "b", "c"}
    assert reference_files(pytester) == {
        f"fake-model-{variant}-{structure}.npz"
        for variant in ("a", "b", "c")
        for structure in STRUCTURES
    }


def test_a_case_runs_the_variants_it_names(pytester):
    write_project(
        pytester,
        contract="ModelReferenceContract",
        case_extra='variants=("b", "c"),',
    )

    run(pytester, "--atomforge-runtime")

    assert requested_variants() == {"b", "c"}


def test_variants_keep_the_case_settings(pytester):
    write_project(
        pytester,
        contract="ModelReferenceContract",
        case_extra=(
            'model_spec_factory=lambda cls: cls(scale=2.0), variants=("b", "c"),'
        ),
    )

    run(pytester, "--atomforge-runtime")

    assert {model.scale for model in requested_models()} == {2.0}


def test_each_variant_is_compared_with_its_own_reference(pytester):
    write_project(pytester, contract="ModelReferenceContract")
    run(pytester, "--atomforge-runtime", "--atomforge-all-variants")

    # Variants shift the energy by different amounts, so a shared reference
    # would fail for some of them.
    _, found = run(pytester, "--atomforge-runtime", "--atomforge-all-variants")

    assert found and outcomes(found) == {"PASSED"}, found


# ModelSpecContract: generated variants and variant_info


def test_spec_contract_passes_for_good_variants_and_variant_info(pytester):
    write_project(
        pytester,
        contract="ModelSpecContract",
        variant_info="variant_fakes:good_variant_info",
    )

    _, found = run(pytester)

    assert found and outcomes(found) == {"PASSED"}, found


def test_spec_contract_passes_without_variant_info(pytester):
    write_project(pytester, contract="ModelSpecContract")

    _, found = run(pytester)

    assert found and outcomes(found) == {"PASSED"}, found


def test_spec_contract_fails_for_duplicate_variant_names(pytester):
    write_project(
        pytester,
        contract="ModelSpecContract",
        model_spec="variant_fakes:DuplicateNamesModel",
    )

    result, found = run(pytester)

    assert "FAILED" in outcomes(found)
    result.stdout.fnmatch_lines(["*dup-name*"])


def test_spec_contract_fails_for_a_default_outside_the_variants(pytester):
    write_project(
        pytester,
        contract="ModelSpecContract",
        model_spec="variant_fakes:DefaultNotCanonicalModel",
    )

    result, found = run(pytester)

    assert "FAILED" in outcomes(found)
    result.stdout.fnmatch_lines(["*inf-omol*"])


def test_spec_contract_fails_for_duplicate_checkpoints(pytester):
    write_project(
        pytester,
        contract="ModelSpecContract",
        variant_info="variant_fakes:shared_checkpoint_variant_info",
    )

    result, found = run(pytester)

    assert "FAILED" in outcomes(found)
    result.stdout.fnmatch_lines(["*ckpt-shared*"])


def test_spec_contract_fails_when_variant_info_misses_a_variant(pytester):
    write_project(
        pytester,
        contract="ModelSpecContract",
        variant_info="variant_fakes:incomplete_variant_info",
    )

    result, found = run(pytester)

    assert "FAILED" in outcomes(found)
    result.stdout.fnmatch_lines(["*fake-model/b*"])


# ModelLocalWeightsContract


def test_bundle_includes_the_local_weights_contract():
    from atomforge_testing import ModelLocalWeightsContract, ModelPluginContract

    assert issubclass(ModelPluginContract, ModelLocalWeightsContract)


def test_local_weights_contract_is_not_collected_without_weights(pytester):
    write_project(pytester, contract="ModelLocalWeightsContract")

    _, found = run(pytester, "--atomforge-runtime")

    assert found == {}


def test_local_weights_contract_is_runtime_gated(pytester):
    write_project(
        pytester,
        contract="ModelLocalWeightsContract",
        model_spec="variant_fakes:WeightedModel",
        case_extra="local_weights_factory=variant_fakes.faithful_weights,",
    )

    _, found = run(pytester)

    assert found and outcomes(found) == {"SKIPPED"}, found
    assert requested_models() == []


def test_local_weights_contract_passes_for_faithful_weights(pytester):
    write_project(
        pytester,
        contract="ModelLocalWeightsContract",
        model_spec="variant_fakes:WeightedModel",
        case_extra="local_weights_factory=variant_fakes.faithful_weights,",
    )

    _, found = run(pytester, "--atomforge-runtime")

    assert found and outcomes(found) == {"PASSED"}, found
    assert any(model.weights is not None for model in requested_models())


def test_local_weights_contract_fails_for_other_parameters(pytester):
    write_project(
        pytester,
        contract="ModelLocalWeightsContract",
        model_spec="variant_fakes:WeightedModel",
        case_extra="local_weights_factory=variant_fakes.wrong_weights,",
    )

    _, found = run(pytester, "--atomforge-runtime")

    assert "FAILED" in outcomes(found), found


def test_local_weights_contract_fails_without_a_factory(pytester):
    write_project(
        pytester,
        contract="ModelLocalWeightsContract",
        model_spec="variant_fakes:WeightedModel",
    )

    result, found = run(pytester, "--atomforge-runtime")

    assert "FAILED" in outcomes(found), found
    result.stdout.fnmatch_lines(["*local_weights_factory*"])


def test_local_weights_contract_fails_when_a_changed_file_is_loaded(pytester):
    # A backend that does not check the hash loads a changed file.
    write_project(
        pytester,
        contract="ModelLocalWeightsContract",
        model_spec="variant_fakes:WeightedModel",
        case_extra="local_weights_factory=variant_fakes.faithful_weights,",
        backend="InProcessBackend",
    )

    _, found = run(pytester, "--atomforge-runtime")

    assert "FAILED" in outcomes(found), found
