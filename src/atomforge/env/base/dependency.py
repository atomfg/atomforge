import json
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path
from urllib.parse import unquote, urlparse

from packaging.requirements import Requirement


def _file_url_to_path(url: str) -> Path:
    parsed = urlparse(url)
    if parsed.scheme != "file":
        raise ValueError(f"Expected file URL, got: {url}")
    return Path(unquote(parsed.path)).resolve()


def _read_direct_url(dist) -> dict | None:
    """The PEP 610 record of where a distribution was installed from, if any."""
    direct_url_text = dist.read_text("direct_url.json")
    if direct_url_text is None:
        return None
    return json.loads(direct_url_text)


def _direct_url_requirement(name: str, data: dict) -> tuple[str, bool]:
    """Turn a PEP 610 record into a requirement that installs the same thing.

    Returns the requirement and whether it is an editable local install.
    """
    url = data.get("url")
    if not url:
        raise RuntimeError(f"Direct install of {name} has no URL")
    subdirectory = data.get("subdirectory")
    fragment = f"#subdirectory={subdirectory}" if subdirectory else ""

    if "vcs_info" in data:
        vcs_info = data["vcs_info"]
        vcs = vcs_info["vcs"]
        commit = vcs_info["commit_id"]
        # PEP 610 stores the URL without the "git+" prefix; tolerate it anyway.
        repo = url.removeprefix(f"{vcs}+")
        return f"{name} @ {vcs}+{repo}@{commit}{fragment}", False

    if "dir_info" in data:
        editable = bool(data["dir_info"].get("editable", False))
        path = _file_url_to_path(url)
        return f"{name} @ file://{path}", editable

    # archive_info: a wheel or sdist from a URL or a local file.
    return f"{name} @ {url}{fragment}", False


def resolve_dependency(requirement_name: str) -> tuple[str, bool]:
    """Pin a requirement to exactly what is installed in the host environment.

    A package installed from a direct source (a local directory, a git repository or
    an archive) is pinned to that source, so the worker installs the same code
    without needing a package index. Anything else is pinned to its installed
    version, e.g. "atomforge-core==1.2.3".

    Returns the requirement and whether it is an editable local install.
    """
    try:
        dist = distribution(requirement_name)
    except PackageNotFoundError as exc:
        raise RuntimeError(
            f"Required distribution is not installed: {requirement_name}"
        ) from exc

    data = _read_direct_url(dist)
    if data is not None:
        return _direct_url_requirement(requirement_name, data)

    return f"{requirement_name}=={dist.version}", False


class ResolvedDependency(Requirement):
    def __init__(self, requirement: str, exact: bool = False):
        editable = False
        if exact:
            requirement, editable = resolve_dependency(requirement)
        super().__init__(requirement)
        self.exact = exact
        self.editable = editable

    @property
    def fingerprint(self) -> str:
        return str(self)
