"""Supported properties and resource capabilities that are functions of the
spec: the contracts check each variant against its own declarations, and
skip, with the variant named, a parameter that only other variants declare.

Uses the inner-session harness of test_variant_contracts.
"""

from atomforge_core.property import Property
from test_variant_contracts import reset_recorders, run, write_project  # noqa: F401
from testing_fakes import InProcessBackend

PER_VARIANT = dict(
    supported_properties="variant_fakes:per_variant_properties",
    resource_capabilities="variant_fakes:per_variant_capabilities",
    case_extra='variants=("a", "c"),',
)


def outcome(found, test, variant, param):
    """The outcome of ``test`` for one variant (first in the parameter id)
    and one parameter (last)."""
    matches = [
        result
        for name, result in found.items()
        if name.startswith(f"{test}[{variant}-") and name.endswith(f"-{param}]")
    ]
    assert len(matches) == 1, (test, parts, found)
    return matches[0]


def test_symbol_contracts_accept_functions_of_the_spec(pytester):
    write_project(pytester, contract="ModelManifestSymbolContract", **PER_VARIANT)

    result, found = run(pytester)

    assert found["test_supported_properties_symbol_is_property_set"] == "PASSED"
    assert found["test_resource_capabilities_symbol_is_resource_capabilities"] == (
        "PASSED"
    )


def test_a_function_that_fails_for_one_variant_fails_the_symbol_contract(pytester):
    write_project(
        pytester,
        contract="ModelManifestSymbolContract",
        **{
            **PER_VARIANT,
            "resource_capabilities": "variant_fakes:broken_for_c_capabilities",
        },
    )

    result, found = run(pytester)

    assert found["test_resource_capabilities_symbol_is_resource_capabilities"] == (
        "FAILED"
    )


def test_each_variant_runs_only_what_it_declares(pytester):
    write_project(pytester, contract="ModelSinglePointRuntimeContract", **PER_VARIANT)

    result, found = run(pytester, "--atomforge-runtime", "-rs")

    strictly = "test_declared_resources_execute_strictly"
    assert outcome(found, strictly, "a", "cpu-f64") == "PASSED"
    assert outcome(found, strictly, "c", "cpu-f64") == "SKIPPED"
    assert outcome(found, strictly, "c", "cpu-f32") == "PASSED"
    returned = "test_declared_property_is_returned"
    assert outcome(found, returned, "a", "stress") == "PASSED"
    assert outcome(found, returned, "c", "stress") == "SKIPPED"
    assert outcome(found, returned, "c", "forces") == "PASSED"
    skips = "\n".join(line for line in result.outlines if "SKIPPED [" in line)
    assert "fake-model/c does not declare cpu-f64" in skips
    assert "fake-model/c does not declare stress" in skips


def test_all_properties_means_what_the_variant_declares(pytester):
    write_project(pytester, contract="ModelResultTypesContract", **PER_VARIANT)

    result, found = run(pytester, "--atomforge-runtime")

    assert "FAILED" not in found.values()
    tasks_for = {"a": [], "c": []}
    for backend in InProcessBackend.instances:
        for task, model, _ in backend.requests:
            if model is not None:
                tasks_for[model.model].append(task)
    assert tasks_for["c"], "the contract ran variant c"
    assert not any(Property.STRESS in task.properties for task in tasks_for["c"])
    assert any(Property.STRESS in task.properties for task in tasks_for["a"])
