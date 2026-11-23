"""Model parameters loaded from a local file or directory instead of a
provider's catalogue, for example a model fine-tuned with the provider's own
package. Identified by a hash of their contents, not by their path."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator

_CHUNK = 1 << 20

# File hashes by (path, size, mtime_ns, inode), so a large file is read once
# per process unless it changes.
_file_hashes: dict[tuple[str, int, int, int], str] = {}


def _file_sha256(path: Path) -> str:
    stat = path.stat()
    key = (str(path), stat.st_size, stat.st_mtime_ns, stat.st_ino)
    cached = _file_hashes.get(key)
    if cached is not None:
        return cached
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK):
            digest.update(chunk)
    sha = digest.hexdigest()
    _file_hashes[key] = sha
    return sha


def _directory_sha256(path: Path) -> str:
    """Hash of the directory's files: each relative path (POSIX form) with the
    hash of its contents, in sorted order. Empty directories do not count."""
    digest = hashlib.sha256()
    files = sorted(
        (p for p in path.rglob("*") if p.is_file()),
        key=lambda p: p.relative_to(path).as_posix(),
    )
    for file in files:
        digest.update(file.relative_to(path).as_posix().encode())
        digest.update(b"\0")
        digest.update(_file_sha256(file).encode())
        digest.update(b"\n")
    return digest.hexdigest()


def weights_sha256(path: Path) -> str:
    """The SHA-256 identifying the weights at ``path``, a file or a
    directory."""
    if path.is_dir():
        return _directory_sha256(path)
    if not path.exists():
        raise FileNotFoundError(f"local weights not found: {path}")
    return _file_sha256(path)


class LocalWeights(BaseModel):
    """Parameters at a local path, identified by their SHA-256.

    ``LocalWeights(path)`` makes the path absolute (the worker's working
    directory may differ) and hashes the file or directory unless ``sha256``
    is given. The hash travels with the spec; the worker calls ``verify()``
    before the model loads the weights, so a file changed in between is an
    error instead of a silent change.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: Path
    sha256: str
    label: str | None = None
    provider_version: str | None = None

    def __init__(self, path: str | os.PathLike | None = None, /, **data: Any):
        if path is not None:
            data["path"] = path
        super().__init__(**data)

    @model_validator(mode="before")
    @classmethod
    def _absolute_path_and_hash(cls, data: Any) -> Any:
        if not isinstance(data, dict) or "path" not in data:
            return data
        path = Path(os.fspath(data["path"])).expanduser().absolute()
        data = {**data, "path": path}
        if data.get("sha256") is None:
            data["sha256"] = weights_sha256(path)
        return data

    def verify(self) -> Path:
        """The path, after checking that its contents still hash to
        ``sha256``."""
        actual = weights_sha256(self.path)
        if actual != self.sha256:
            raise ValueError(
                f"local weights at {self.path} have changed: sha256 is "
                f"{actual}, expected {self.sha256}"
            )
        return self.path

    @property
    def short_sha256(self) -> str:
        return self.sha256[:8]
