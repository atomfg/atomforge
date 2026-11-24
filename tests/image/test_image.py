"""Acceptance test for "Containers, design" in the engineering log: an image
built from `containers/Dockerfile` runs single points offline from its
preloaded environments.

The image is built from a host project made here: the atomforge working tree
(so the test checks the current code) and the model plugin template, a torch
plugin that downloads nothing. The container runs with a read-only root
filesystem, no network, a writable `/cache`, the local weights bound at the
same absolute path, and uv off PATH (see run_in_image.py). Each energy must
equal the same calculation run outside the image.

The image's `python` is the host environment's (first on PATH). Run with
`just test-image`. Needs docker with buildx; the platform defaults
to linux/amd64 (the cluster's) and can be set with ATOMFORGE_IMAGE_PLATFORM.
"""

import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path

import pytest

pytestmark = pytest.mark.image

ATOMFORGE = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PLATFORM = os.environ.get("ATOMFORGE_IMAGE_PLATFORM", "linux/amd64")
PRELOAD = "ase-lj torch-lj"

HOST_PYPROJECT = """\
[project]
name = "atomforge-image-test"
version = "0"
requires-python = ">=3.12"
dependencies = [
    "atomforge",
    "atomforge-core",
    "atomforge-runtime",
    "atomforge-builtins",
    "atomforge-template",
]

[tool.uv]
package = false

[tool.uv.sources]
atomforge = { path = "atomforge", editable = true }
atomforge-core = { path = "atomforge/packages/atomforge-core", editable = true }
atomforge-runtime = { path = "atomforge/packages/atomforge-runtime", editable = true }
atomforge-builtins = { path = "atomforge/packages/atomforge-builtins", editable = true }
atomforge-template = { path = "atomforge/templates/model-plugin", editable = true }
"""


def run(command, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(command, check=True, text=True, **kwargs)


def working_tree_files() -> list[str]:
    listed = run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ATOMFORGE,
        capture_output=True,
    ).stdout
    return [
        name for name in listed.split("\0") if name and (ATOMFORGE / name).is_file()
    ]


@pytest.fixture(scope="module")
def host_project(tmp_path_factory) -> Path:
    project = tmp_path_factory.mktemp("host")
    for name in working_tree_files():
        target = project / "atomforge" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ATOMFORGE / name, target)
    (project / "pyproject.toml").write_text(HOST_PYPROJECT)
    run(["uv", "lock"], cwd=project)
    return project


@pytest.fixture(scope="module")
def image(host_project):
    if shutil.which("docker") is None:
        pytest.fail("docker is not on PATH")
    tag = f"atomforge-image-test:{uuid.uuid4().hex[:12]}"
    run(
        [
            "docker",
            "buildx",
            "build",
            "--platform",
            PLATFORM,
            "--file",
            str(ATOMFORGE / "containers" / "Dockerfile"),
            "--build-arg",
            f"PRELOAD={PRELOAD}",
            "--tag",
            tag,
            "--load",
            str(host_project),
        ]
    )
    yield tag
    subprocess.run(["docker", "image", "rm", "--force", tag], check=False)


@pytest.fixture(scope="module")
def weights(tmp_path_factory) -> Path:
    path = tmp_path_factory.mktemp("weights") / "torch-lj.json"
    path.write_text(json.dumps({"epsilon": 0.0104, "sigma": 3.4}))
    return path


@pytest.fixture(scope="module")
def in_image(image, weights, tmp_path_factory):
    cache = tmp_path_factory.mktemp("cache")
    completed = run(
        [
            "docker",
            "run",
            "--rm",
            "--platform",
            PLATFORM,
            "--read-only",
            "--network",
            "none",
            "--tmpfs",
            "/tmp",
            "--volume",
            f"{cache}:/cache",
            "--volume",
            f"{weights.parent}:{weights.parent}:ro",
            "--volume",
            f"{HERE}:/test:ro",
            image,
            "python",
            "/test/run_in_image.py",
            str(weights),
        ],
        capture_output=True,
    )
    output = json.loads(completed.stdout.strip().splitlines()[-1])
    return output, cache


@pytest.fixture(scope="module")
def outside_image(host_project, weights, tmp_path_factory):
    """The same calculations on this machine, outside any container, from the
    same host project. The environments are preloaded into a search path,
    since run_in_image.py takes uv off PATH."""
    run(["uv", "sync", "--locked"], cwd=host_project)
    bin_dir = host_project / ".venv" / "bin"
    preloaded = tmp_path_factory.mktemp("preloaded")
    env = {**os.environ, "ATOMFORGE_ENV_INSTALL_PATH": str(preloaded)}
    run([str(bin_dir / "atomforge"), "env", "preload", *PRELOAD.split()], env=env)
    env = {
        **os.environ,
        "ATOMFORGE_ENV_SEARCH_PATHS": str(preloaded),
        "ATOMFORGE_ENV_INSTALL_PATH": str(tmp_path_factory.mktemp("install")),
    }
    completed = run(
        [str(bin_dir / "python"), str(HERE / "run_in_image.py"), str(weights)],
        env=env,
        capture_output=True,
    )
    return json.loads(completed.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize("model", PRELOAD.split())
def test_energy_in_image_equals_energy_outside(in_image, outside_image, model):
    output, _ = in_image

    assert output["results"][model]["energy"] == pytest.approx(
        outside_image["results"][model]["energy"], rel=1e-6
    )


@pytest.mark.parametrize("model", PRELOAD.split())
def test_preloaded_environment_is_used(in_image, model):
    output, _ = in_image

    assert output["results"][model]["environment_path"].startswith(
        "/opt/atomforge/envs/"
    )


def test_nothing_is_built_at_run_time(in_image):
    output, cache = in_image

    assert output["warnings"] == []
    built = cache / "atomforge" / "envs" / "uv"
    assert not built.exists() or not any(built.iterdir())
