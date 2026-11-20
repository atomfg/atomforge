from atomforge.env.base.dependency import ResolvedDependency
from atomforge.env.uv.uv_pyproject_writer import UVPyprojectWriter


def test_uv_pyproject_writer_preserves_pep440_python_range():
    writer = UVPyprojectWriter(
        env_name="orb-tested",
        python_version="<3.13,>=3.12",
        dependencies=[],
    )

    pyproject = writer.to_pyproject()

    assert 'requires-python = "<3.13,>=3.12"' in pyproject


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
        extras={"uv.find-links": ('["https://data.pyg.org/whl/torch-2.4.1+cpu.html"]')},
    )

    pyproject = writer.to_pyproject()

    assert "[tool.uv]" in pyproject
    assert 'find-links = ["https://data.pyg.org/whl/torch-2.4.1+cpu.html"]' in pyproject


# A fixed project name (engineering log: "A fixed project name for worker
# environments, design").


def _project_name(pyproject: str) -> str:
    import tomllib

    return tomllib.loads(pyproject)["project"]["name"]


def test_worker_project_name_is_fixed():
    names = {
        _project_name(
            UVPyprojectWriter(
                env_name=env_name, python_version=">=3.12", dependencies=[]
            ).to_pyproject()
        )
        for env_name in ("torch-lj", "orb-v3", "mace")
    }

    assert names == {"atomforge-worker"}


def test_environment_named_like_a_requirement_is_not_its_own_dependency():
    writer = UVPyprojectWriter(
        env_name="tace",
        python_version=">=3.12",
        dependencies=[ResolvedDependency("tace>=0.2.4", exact=False)],
    )

    assert _project_name(writer.to_pyproject()) == "atomforge-worker"


def test_environment_name_is_kept_as_a_comment():
    writer = UVPyprojectWriter(
        env_name="tace", python_version=">=3.12", dependencies=[]
    )

    assert writer.to_pyproject().startswith("# atomforge environment: tace\n")
