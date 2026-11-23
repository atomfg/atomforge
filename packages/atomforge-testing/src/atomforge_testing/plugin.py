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
    group.addoption(
        "--atomforge-all-variants",
        action="store_true",
        default=False,
        help=(
            "Run the runtime contracts for every generated variant of a case's "
            "spec, instead of the case's own spec or the variants it names."
        ),
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "atomforge_local_weights: a local weights contract test, collected only "
        "when the case's spec declares weights",
    )
    for marker, (option, help_text) in GATES.items():
        config.addinivalue_line(
            "markers", f"{marker}: {help_text}; enabled by {option}"
        )


def _option_enabled(config: pytest.Config, option: str) -> bool:
    return bool(config.getoption(option.lstrip("-").replace("-", "_")))


def _declares_weights(case) -> bool:
    try:
        spec_cls = case.manifest.model_spec.load_symbol()
    except Exception:  # noqa: BLE001 - reported by the symbol contract
        return True
    return spec_cls.accepts_local_weights()


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    deselected = []
    for item in items:
        if item.get_closest_marker("atomforge_local_weights") is None:
            continue
        case = getattr(item.cls, "manifest_case", None)
        if case is not None and not _declares_weights(case):
            deselected.append(item)
    if deselected:
        config.hook.pytest_deselected(items=deselected)
        items[:] = [item for item in items if item not in deselected]

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
    from atomforge_testing.variants import selected_variant_names

    if (
        "atomforge_variant" in metafunc.fixturenames
        and metafunc.definition.get_closest_marker("atomforge_runtime") is not None
    ):
        names = selected_variant_names(case, metafunc.config)
        if names is not None and len(names) > 1:
            metafunc.parametrize("atomforge_variant", names, ids=names)

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


@pytest.fixture
def atomforge_variant(request) -> str | None:
    """The variant name a runtime contract test runs, or None for the case's
    own spec. Parametrized when a case selects several variants."""
    case = getattr(request.cls, "manifest_case", None)
    if case is None or request.node.get_closest_marker("atomforge_runtime") is None:
        return None
    from atomforge_testing.variants import selected_variant_names

    names = selected_variant_names(case, request.config)
    return names[0] if names else None


@pytest.fixture(scope="session")
def atomforge_result_descriptions() -> dict:
    """Descriptions computed by ``ModelResultTypesContract``, kept for the
    session so that its checks share one task run per request."""
    return {}
