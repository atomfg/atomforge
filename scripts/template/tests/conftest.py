import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run-exported-tests",
        action="store_true",
        default=False,
        help="Run the exported template's own test suite (builds its worker "
        "environment).",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "exported_tests: runs the exported template's tests"
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("run_exported_tests"):
        return
    skip = pytest.mark.skip(reason="pass --run-exported-tests to run")
    for item in items:
        if "exported_tests" in item.keywords:
            item.add_marker(skip)
