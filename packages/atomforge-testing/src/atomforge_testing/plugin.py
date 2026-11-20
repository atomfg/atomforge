"""The atomforge-testing pytest plugin, registered through the ``pytest11`` entry
point. Installing atomforge-testing is enough to get its options, markers and
fixtures.

The command-line options are the only gates for the expensive contracts. The
markers select (``-m``) but never enable anything.
"""

from __future__ import annotations

import pytest

GATES = {
    "atomforge_environment": (
        "--atomforge-environment",
        "resolve model environments with the environment provider",
    ),
    "atomforge_runtime": (
        "--atomforge-runtime",
        "execute models through a backend in their worker environment",
    ),
    "atomforge_cuda": (
        "--atomforge-cuda",
        "execute models on an NVIDIA GPU through CUDA (needs a machine with one)",
    ),
    "atomforge_rocm": (
        "--atomforge-rocm",
        "execute models on an AMD GPU through ROCm (needs a machine with one)",
    ),
    "atomforge_mps": (
        "--atomforge-mps",
        "execute models on Apple's MPS (needs a Mac with Apple silicon)",
    ),
}


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("atomforge", "AtomForge plugin contracts")
    for option, help_text in GATES.values():
        group.addoption(
            option,
            action="store_true",
            default=False,
            help=f"Run the contracts that {help_text}.",
        )


def pytest_configure(config: pytest.Config) -> None:
    for marker, (option, help_text) in GATES.items():
        config.addinivalue_line(
            "markers", f"{marker}: {help_text}; enabled by {option}"
        )


def _option_enabled(config: pytest.Config, option: str) -> bool:
    return bool(config.getoption(option.lstrip("-").replace("-", "_")))


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    for marker, (option, _) in GATES.items():
        if _option_enabled(config, option):
            continue
        skip = pytest.mark.skip(reason=f"pass {option} to run")
        for item in items:
            if item.get_closest_marker(marker) is not None:
                item.add_marker(skip)


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Parametrize contract tests from the case's manifest: one test per
    declared property, declared resource combination and environment
    profile."""
    case = getattr(metafunc.cls, "manifest_case", None)
    if case is None:
        return

    from atomforge_testing.capabilities import PARAMETRIZATIONS

    for argname, parametrization in PARAMETRIZATIONS.items():
        if argname in metafunc.fixturenames:
            metafunc.parametrize(argname, parametrization(case))


@pytest.fixture(scope="session")
def atomforge_backend():
    """One backend for every runtime contract in the session, shut down at the
    end of it. Override this fixture to run the contracts against another
    backend."""
    import atomforge.backend.subprocess as subprocess_backend

    with subprocess_backend.SubprocessBackend() as backend:
        yield backend


@pytest.fixture(scope="session")
def atomforge_result_descriptions() -> dict:
    """Descriptions computed by ``ModelResultTypesContract``, kept for the
    session so that its checks share one task run per request."""
    return {}
