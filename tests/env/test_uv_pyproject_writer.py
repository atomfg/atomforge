from atomforge.env.base.dependency import ResolvedDependency
from atomforge.env.uv.uv_pyproject_writer import UVPyprojectWriter


def test_uv_pyproject_writer_emits_extra_build_dependencies():
    writer = UVPyprojectWriter(
        env_name="fairchem-legacy",
        python_version=">=3.12",
        dependencies=[
            ResolvedDependency("torch", exact=False),
            ResolvedDependency("torch-scatter", exact=False),
        ],
        extras={"uv.extra-build-dependencies.torch-scatter": '["torch"]'},
    )

    pyproject = writer.to_pyproject()

    assert "[tool.uv.extra-build-dependencies]" in pyproject
    assert 'torch-scatter = ["torch"]' in pyproject


def test_uv_pyproject_writer_emits_find_links():
    writer = UVPyprojectWriter(
        env_name="fairchem-legacy",
        python_version=">=3.12",
        dependencies=[ResolvedDependency("torch-scatter", exact=False)],
        extras={
            "uv.find-links": (
                '["https://data.pyg.org/whl/torch-2.4.1+cpu.html"]'
            )
        },
    )

    pyproject = writer.to_pyproject()

    assert "[tool.uv]" in pyproject
    assert (
        'find-links = ["https://data.pyg.org/whl/torch-2.4.1+cpu.html"]'
        in pyproject
    )
