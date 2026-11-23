import pytest

from atomforge_core.structure import StructureData


@pytest.fixture
def example_structure():
    return StructureData(
        positions=[[4.5, 0, 0], [5.5, 0, 0]],
        cell=[[10, 0, 0], [0, 10, 0], [0, 0, 10]],
        numbers=[1, 8],
        pbc=[False, False, False],
    )


def pytest_addoption(parser):
    parser.addoption(
        "--image",
        action="store_true",
        default=False,
        help="Build the container image and run in it (slow; needs docker).",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--image"):
        return
    skip = pytest.mark.skip(reason="needs --image (see `just test-image`)")
    for item in items:
        if "image" in item.keywords:
            item.add_marker(skip)
