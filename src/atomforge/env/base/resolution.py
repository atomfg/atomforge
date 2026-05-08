from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EnvironmentResolutionResult:
    provider: str
    success: bool
    message: str | None = None
    stdout: str = ""
    stderr: str = ""
    project_path: Path | None = None
    command: tuple[str, ...] | None = None
