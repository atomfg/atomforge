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


def _check_if_editable(dist: distribution) -> tuple[bool, str | None]:
    direct_url_text = dist.read_text("direct_url.json")
    if direct_url_text is None:
        return False, None

    data = json.loads(direct_url_text)
    dir_info = data.get("dir_info") or {}
    editable = bool(dir_info.get("editable", False))
    url = data.get("url")
    return editable, url


def resolve_dependency(requirement_name: str):
    """
    Check if a requirement has a local file source (e.g., "atomforge @ file:///path/to/atomforge") and add a "source" attribute to the requirement if it does.
    """
    try:
        dist = distribution(requirement_name)
    except PackageNotFoundError as exc:
        raise RuntimeError(
            f"Required distribution is not installed: {requirement_name}"
        ) from exc
    
    editable, url = _check_if_editable(dist)

    if editable:
        if not url:
            raise RuntimeError(f"Editable install for {requirement_name} has no URL")
        path = _file_url_to_path(url)
        resolved_requirement = f"{requirement_name} @ file://{path}"


    else: # Add the version of the locally installed package as a specifier (e.g., "atomforge @ file:///path/to/atomforge" becomes "atomforge==1.2.3")
        path = None
        version = dist.version
        resolved_requirement = f"{requirement_name}=={version}"

    return resolved_requirement

class ResolvedDependency(Requirement):
    def __init__(self, requirement: str, exact: bool = False):        
        if exact:                
            requirement = resolve_dependency(requirement)
        super().__init__(requirement)
        self.exact = exact

    @property
    def fingerprint(self) -> str:
        return str(self)
