import json
from importlib.metadata import PackageNotFoundError

import pytest

from atomforge.env.base import dependency
from atomforge.env.base.dependency import ResolvedDependency, resolve_dependency
from atomforge.env.uv.uv_pyproject_writer import UVPyprojectWriter


class FakeDistribution:
    def __init__(self, version="1.2.3", direct_url=None):
        self.version = version
        self._direct_url = direct_url

    def read_text(self, filename):
        assert filename == "direct_url.json"
        return None if self._direct_url is None else json.dumps(self._direct_url)


@pytest.fixture
def installed(monkeypatch):
    """Install fake distributions: installed(name, **FakeDistribution kwargs)."""
    dists = {}

    def lookup(name):
        try:
            return dists[name]
        except KeyError:
            raise PackageNotFoundError(name) from None

    monkeypatch.setattr(dependency, "distribution", lookup)

    def install(name, **kwargs):
        dists[name] = FakeDistribution(**kwargs)

    return install


def test_index_install_is_pinned_to_its_version(installed):
    installed("pkg", version="1.2.3")

    assert resolve_dependency("pkg") == ("pkg==1.2.3", False)


def test_editable_install_is_forwarded_as_editable_path(installed, tmp_path):
    installed(
        "pkg",
        direct_url={"url": tmp_path.as_uri(), "dir_info": {"editable": True}},
    )

    assert resolve_dependency("pkg") == (f"pkg @ file://{tmp_path.resolve()}", True)


def test_non_editable_directory_install_is_forwarded_as_path(installed, tmp_path):
    installed("pkg", direct_url={"url": tmp_path.as_uri(), "dir_info": {}})

    assert resolve_dependency("pkg") == (f"pkg @ file://{tmp_path.resolve()}", False)


def test_git_install_is_forwarded_pinned_to_its_commit(installed):
    installed(
        "atomforge-core",
        direct_url={
            "url": "https://github.com/atomfg/atomforge",
            "vcs_info": {
                "vcs": "git",
                "commit_id": "0123abcd",
                "requested_revision": "v26.11.18",
            },
            "subdirectory": "packages/atomforge-core",
        },
    )

    requirement, editable = resolve_dependency("atomforge-core")

    assert requirement == (
        "atomforge-core @ git+https://github.com/atomfg/atomforge@0123abcd"
        "#subdirectory=packages/atomforge-core"
    )
    assert not editable


def test_git_url_with_vcs_prefix_is_not_doubled(installed):
    installed(
        "pkg",
        direct_url={
            "url": "git+https://example.com/pkg.git",
            "vcs_info": {"vcs": "git", "commit_id": "abc"},
        },
    )

    assert resolve_dependency("pkg") == (
        "pkg @ git+https://example.com/pkg.git@abc",
        False,
    )


def test_archive_install_is_forwarded_as_url(installed):
    url = "https://example.com/pkg-1.0-py3-none-any.whl"
    installed("pkg", direct_url={"url": url, "archive_info": {}})

    assert resolve_dependency("pkg") == (f"pkg @ {url}", False)


def test_missing_distribution_raises(installed):
    with pytest.raises(RuntimeError, match="not installed"):
        resolve_dependency("missing")


def test_writer_adds_uv_source_only_for_editable_installs(installed, tmp_path):
    editable_dir = tmp_path / "editable"
    plain_dir = tmp_path / "plain"
    installed(
        "editable-pkg",
        direct_url={"url": editable_dir.as_uri(), "dir_info": {"editable": True}},
    )
    installed("plain-pkg", direct_url={"url": plain_dir.as_uri(), "dir_info": {}})
    installed(
        "git-pkg",
        direct_url={
            "url": "https://example.com/git-pkg",
            "vcs_info": {"vcs": "git", "commit_id": "abc"},
        },
    )

    writer = UVPyprojectWriter(
        env_name="env",
        python_version=">=3.12",
        dependencies=[
            ResolvedDependency("editable-pkg", exact=True),
            ResolvedDependency("plain-pkg", exact=True),
            ResolvedDependency("git-pkg", exact=True),
        ],
    )

    pyproject = writer.to_pyproject()

    sources = pyproject.split("[tool.uv.sources]", 1)[1]
    assert "editable-pkg = { path" in sources
    assert "plain-pkg" not in sources
    assert "git-pkg" not in sources
    assert '"git-pkg @ git+https://example.com/git-pkg@abc"' in pyproject
