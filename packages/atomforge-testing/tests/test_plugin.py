"""Acceptance tests for the atomforge-testing pytest plugin (step 1 of the
"Extending atomforge-testing" design entry in the engineering log).

Each test runs an inner pytest session with `pytester`, in process, so that the
plugin's options, markers, gating and fixtures are exercised the way a plugin's
test suite sees them.
"""

from pathlib import Path
import sys

import pytest

from atomforge_core.model.result import ModelResult
import atomforge_testing
from atomforge_testing import (
    ModelEnvironmentContract,
    ModelEnvironmentResolutionContract,
    ModelManifestContract,
    ModelManifestSymbolContract,
    ModelRegistryContract,
    ModelSinglePointRuntimeContract,
    ModelSpecContract,
)

TESTS_PATH = Path(__file__).resolve().parent

if str(TESTS_PATH) not in sys.path:
    sys.path.insert(0, str(TESTS_PATH))


PYPROJECT = """\
[project]
name = "fake-plugin"

[project.entry-points.'atomforge.model']
fake = "testing_fakes:fake_manifest"
"""

CASE_MODULE = """\
from pathlib import Path

from atomforge_core.registry.model_manifest import ModelManifest
from atomforge_testing import ModelManifestCase

PYPROJECT = Path(__file__).parent / "pyproject.toml"

MANIFEST = ModelManifest(
    kind="fake-model",
    model_spec="testing_fakes:FakeModel",
    executor_cls="testing_fakes:FakeModelExecutor",
    supported_properties="testing_fakes:FakeSupportedProperties",
    environment_factory_cls="testing_fakes:FakeEnvironmentFactory",
    metadata="testing_fakes:FakeMetadata",
    resource_capabilities="testing_fakes:FakeResourceCapabilities",
    distribution="fake-plugin",
)

CASE = ModelManifestCase(
    manifest=MANIFEST,
    entry_point_name="fake",
    entry_point_package="fake-plugin",
    pyproject_path=PYPROJECT,
    expected_entry_point_target="testing_fakes:fake_manifest",
)
"""

RESOLUTION_TESTS = """\
from fake_case import CASE
from atomforge_testing import ModelEnvironmentResolutionContract


class TestFake(ModelEnvironmentResolutionContract):
    manifest_case = CASE
"""

RUNTIME_TESTS = """\
from fake_case import CASE
from atomforge_testing import ModelSinglePointRuntimeContract


class TestFake(ModelSinglePointRuntimeContract):
    manifest_case = CASE


class TestFakeAgain(ModelSinglePointRuntimeContract):
    manifest_case = CASE
"""

FAKE_BACKEND_CONFTEST = """\
import pytest

from atomforge_core.model.result import ModelResult


class FakeBackend:
    def execute(self, task, model=None, exec_resources=None, timeout=None):
        n_atoms = len(task.structure.numbers)
        return ModelResult(energy=1.0, forces=[[0.0, 0.0, 0.0]] * n_atoms)


@pytest.fixture(scope="session")
def atomforge_backend():
    return FakeBackend()
"""


@pytest.fixture
def plugin_project(pytester):
    """A directory laid out like a plugin's tests, with no marker registration
    and no conftest of its own."""
    pytester.makefile(".toml", pyproject=PYPROJECT)
    pytester.makepyfile(fake_case=CASE_MODULE)
    pytester.syspathinsert()
    return pytester


class FakeResolutionResult:
    success = True
    provider = "fake"
    command = ("fake", "resolve")
    project_path = Path("/tmp/fake-project")
    message = None
    stdout = ""
    stderr = ""


class FakeUVEnvironmentProvider:
    resolved = []

    def __init__(self, *args, **kwargs):
        pass

    def resolve_environment(self, spec):
        type(self).resolved.append(spec)
        return FakeResolutionResult()


@pytest.fixture
def fake_uv_provider(monkeypatch):
    import atomforge.env.uv

    FakeUVEnvironmentProvider.resolved = []
    monkeypatch.setattr(
        atomforge.env.uv, "UVEnvironmentProvider", FakeUVEnvironmentProvider
    )
    return FakeUVEnvironmentProvider


# Gating: environment resolution


def test_resolution_contract_is_skipped_without_option(
    plugin_project, fake_uv_provider
):
    plugin_project.makepyfile(test_contracts=RESOLUTION_TESTS)

    result = plugin_project.runpytest_inprocess()

    result.assert_outcomes(skipped=1)
    assert fake_uv_provider.resolved == []


def test_negated_marker_expression_does_not_enable_resolution(
    plugin_project, fake_uv_provider
):
    plugin_project.makepyfile(test_contracts=RESOLUTION_TESTS)

    result = plugin_project.runpytest_inprocess("-m", "not atomforge_environment")

    result.assert_outcomes(deselected=1)
    assert fake_uv_provider.resolved == []


def test_marker_expression_alone_does_not_enable_resolution(
    plugin_project, fake_uv_provider
):
    plugin_project.makepyfile(test_contracts=RESOLUTION_TESTS)

    result = plugin_project.runpytest_inprocess("-m", "atomforge_environment")

    result.assert_outcomes(skipped=1)
    assert fake_uv_provider.resolved == []


def test_resolution_contract_runs_with_option(plugin_project, fake_uv_provider):
    plugin_project.makepyfile(test_contracts=RESOLUTION_TESTS)

    result = plugin_project.runpytest_inprocess("--atomforge-environment")

    result.assert_outcomes(passed=1)
    assert len(fake_uv_provider.resolved) == 1


# Gating: runtime


def test_runtime_contracts_are_skipped_without_option(plugin_project):
    plugin_project.makeconftest(FAKE_BACKEND_CONFTEST)
    plugin_project.makepyfile(test_contracts=RUNTIME_TESTS)

    result = plugin_project.runpytest_inprocess()

    result.assert_outcomes(skipped=4)


def test_runtime_environment_variable_no_longer_enables_runtime(
    plugin_project, monkeypatch
):
    monkeypatch.setenv("ATOMFORGE_RUN_RUNTIME_TESTS", "1")
    plugin_project.makeconftest(FAKE_BACKEND_CONFTEST)
    plugin_project.makepyfile(test_contracts=RUNTIME_TESTS)

    result = plugin_project.runpytest_inprocess()

    result.assert_outcomes(skipped=4)


def test_runtime_contracts_run_with_option(plugin_project):
    plugin_project.makeconftest(FAKE_BACKEND_CONFTEST)
    plugin_project.makepyfile(test_contracts=RUNTIME_TESTS)

    result = plugin_project.runpytest_inprocess("--atomforge-runtime")

    result.assert_outcomes(passed=4)


def test_gpu_marker_is_gated_by_gpu_option(plugin_project):
    plugin_project.makepyfile(
        test_gpu="""
        import pytest

        @pytest.mark.atomforge_gpu
        def test_on_gpu():
            pass
        """
    )

    plugin_project.runpytest_inprocess().assert_outcomes(skipped=1)
    plugin_project.runpytest_inprocess("--atomforge-gpu").assert_outcomes(passed=1)


# Markers


def test_markers_are_registered_by_the_plugin(plugin_project):
    result = plugin_project.runpytest_inprocess("--markers")

    result.stdout.fnmatch_lines(
        [
            "@pytest.mark.atomforge_environment*",
            "@pytest.mark.atomforge_runtime*",
            "@pytest.mark.atomforge_gpu*",
        ],
        consecutive=False,
    )


def test_contracts_collect_under_strict_markers(plugin_project):
    plugin_project.makeconftest(FAKE_BACKEND_CONFTEST)
    plugin_project.makepyfile(
        test_resolution=RESOLUTION_TESTS, test_runtime=RUNTIME_TESTS
    )

    result = plugin_project.runpytest_inprocess("--strict-markers", "-W", "error")

    result.assert_outcomes(skipped=5)


# The shared backend


class RecordingBackend:
    events: list[str] = []

    def __init__(self, *args, **kwargs):
        type(self).events.append("init")

    def __enter__(self):
        type(self).events.append("enter")
        return self

    def __exit__(self, *exc_info):
        type(self).events.append("exit")

    def execute(self, task, model=None, exec_resources=None, timeout=None):
        type(self).events.append("execute")
        n_atoms = len(task.structure.numbers)
        return ModelResult(energy=1.0, forces=[[0.0, 0.0, 0.0]] * n_atoms)


def test_runtime_contracts_share_one_backend_closed_at_session_end(
    plugin_project, monkeypatch
):
    import atomforge.backend.subprocess

    RecordingBackend.events = []
    monkeypatch.setattr(
        atomforge.backend.subprocess, "SubprocessBackend", RecordingBackend
    )
    plugin_project.makepyfile(test_contracts=RUNTIME_TESTS)

    result = plugin_project.runpytest_inprocess("--atomforge-runtime")

    result.assert_outcomes(passed=4)
    assert RecordingBackend.events == [
        "init",
        "enter",
        "execute",
        "execute",
        "execute",
        "execute",
        "exit",
    ]


def test_no_backend_is_created_when_runtime_is_disabled(plugin_project, monkeypatch):
    import atomforge.backend.subprocess

    RecordingBackend.events = []
    monkeypatch.setattr(
        atomforge.backend.subprocess, "SubprocessBackend", RecordingBackend
    )
    plugin_project.makepyfile(test_contracts=RUNTIME_TESTS)

    plugin_project.runpytest_inprocess().assert_outcomes(skipped=4)

    assert RecordingBackend.events == []


# The bundle class


CONTRACTS = (
    ModelManifestContract,
    ModelManifestSymbolContract,
    ModelSpecContract,
    ModelRegistryContract,
    ModelEnvironmentContract,
    ModelEnvironmentResolutionContract,
    ModelSinglePointRuntimeContract,
)


def contract_test_names(cls) -> set[str]:
    return {name for name in dir(cls) if name.startswith("test_")}


def test_bundle_is_exported():
    assert "ModelPluginContract" in atomforge_testing.__all__


def test_bundle_includes_every_contract():
    from atomforge_testing import ModelPluginContract

    for contract in CONTRACTS:
        assert issubclass(ModelPluginContract, contract), contract.__name__


def test_bundle_collects_every_contract_test(plugin_project):
    from atomforge_testing import ModelPluginContract

    expected = set().union(*(contract_test_names(c) for c in CONTRACTS))
    plugin_project.makepyfile(
        test_bundle="""
        from fake_case import CASE
        from atomforge_testing import ModelPluginContract


        class TestFake(ModelPluginContract):
            manifest_case = CASE
        """
    )

    result = plugin_project.runpytest_inprocess("--collect-only", "-q")

    collected = {
        line.split("::")[-1].split("[")[0] for line in result.outlines if "::" in line
    }
    assert contract_test_names(ModelPluginContract) == expected
    assert collected == expected


def test_bundle_marks_only_gated_tests(plugin_project):
    """Marks must not leak from one contract to the others through the MRO of
    the bundle class."""
    plugin_project.makepyfile(
        test_bundle="""
        from fake_case import CASE
        from atomforge_testing import ModelPluginContract


        class TestFake(ModelPluginContract):
            manifest_case = CASE
        """
    )

    def collected(*args):
        result = plugin_project.runpytest_inprocess("--collect-only", "-q", *args)
        return {
            line.split("::")[-1].split("[")[0]
            for line in result.outlines
            if "::" in line
        }

    runtime = collected("-m", "atomforge_runtime")
    environment = collected("-m", "atomforge_environment")

    assert runtime == contract_test_names(ModelSinglePointRuntimeContract)
    assert environment == contract_test_names(ModelEnvironmentResolutionContract)
