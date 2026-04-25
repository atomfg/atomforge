from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path
from urllib.parse import urlparse, unquote
import json


@dataclass(frozen=True)
class ResolvedDependency:
    name: str
    dependency_entry: str
    uv_source: dict | None
    fingerprint: str

    def get_source_entry(self) -> str:
        if self.uv_source:
            return f'{{path = "{self.uv_source["path"]}", editable = true}}'


def _normalize_dist_name(name: str) -> str:
    return name.lower().replace("_", "-")


def _file_url_to_path(url: str) -> Path:
    parsed = urlparse(url)
    if parsed.scheme != "file":
        raise ValueError(f"Expected file URL, got: {url}")
    return Path(unquote(parsed.path)).resolve()


def resolve_distribution(name: str) -> ResolvedDependency:
    try:
        dist = distribution(name)
    except PackageNotFoundError as exc:
        raise RuntimeError(f"Required distribution is not installed: {name}") from exc

    canonical_name = _normalize_dist_name(dist.metadata["Name"])
    direct_url_text = dist.read_text("direct_url.json")

    if direct_url_text is None:
        return ResolvedDependency(
            name=canonical_name,
            dependency_entry=f"{canonical_name}=={dist.version}",
            uv_source=None,
            fingerprint=f"version:{canonical_name}=={dist.version}",
        )

    data = json.loads(direct_url_text)
    url = data.get("url")
    dir_info = data.get("dir_info") or {}
    editable = bool(dir_info.get("editable", False))

    if editable:
        if not url:
            raise RuntimeError(f"Editable install for {canonical_name} has no URL")
        path = _file_url_to_path(url)
        return ResolvedDependency(
            name=canonical_name,
            dependency_entry=canonical_name,
            uv_source={"path": path.as_posix()},
            fingerprint=f"editable:{canonical_name}:{path.as_posix()}",
        )

    return ResolvedDependency(
        name=canonical_name,
        dependency_entry=f"{canonical_name}=={dist.version}",
        uv_source=None,
        fingerprint=f"version:{canonical_name}=={dist.version}",
    )