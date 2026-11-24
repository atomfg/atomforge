from abc import ABC, abstractmethod
from dataclasses import dataclass
import hashlib
import json

from atomforge_core.env.env import EnvironmentSpec
from atomforge_core.provenance import EnvironmentProvenance
from atomforge.env.base.handle import EnvironmentHandle
from atomforge.env.base.info import EnvironmentInfo
from atomforge.env.base.resolution import EnvironmentResolutionResult

from pathlib import Path


def file_sha256(path: Path) -> str | None:
    if not path.exists():
        return None

    hasher = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


MARKER_FILE = "atomforge-env.json"
"""Written into an environment's directory once it has been built. Only an
environment with a marker is used from a preloaded (read-only) search path."""


@dataclass(frozen=True)
class EnvironmentMarker:
    key: str
    name: str
    spec_hash: str
    lockfile_hash: str | None = None

    def write(self, directory: Path) -> None:
        (directory / MARKER_FILE).write_text(
            json.dumps(self.__dict__, indent=2, sort_keys=True) + "\n"
        )

    @classmethod
    def read(cls, directory: Path) -> "EnvironmentMarker | None":
        try:
            data = json.loads((directory / MARKER_FILE).read_text())
            return cls(**data)
        except (OSError, ValueError, TypeError):
            return None


@dataclass(frozen=True)
class ListedEnvironment:
    key: str
    name: str | None
    path: Path
    read_only: bool


class EnvironmentProvider(ABC):
    def __init__(
        self,
        search_path: tuple[Path, ...],
        install_path: Path,
        *,
        warn_when_building: bool = True,
    ):
        # Warn when an environment is built while preloaded search paths are
        # configured. Off for deliberate builds (`atomforge env preload`).
        self.warn_when_building = warn_when_building
        self.install_path = (
            Path(install_path) if install_path else Path.home() / ".atomforge" / "envs"
        )
        self.install_path.mkdir(parents=True, exist_ok=True)

        self.search_paths = tuple(Path(p) for p in search_path if Path(p).exists())
        if not any(self.is_install_path(p) for p in self.search_paths):
            self.search_paths = (self.install_path,) + self.search_paths

    def is_install_path(self, path: Path) -> bool:
        return Path(path).resolve() == self.install_path.resolve()

    @property
    def preloaded_paths(self) -> tuple[Path, ...]:
        """The search paths other than the install path. Environments there
        are read-only: used as they are, never checked or removed."""
        return tuple(p for p in self.search_paths if not self.is_install_path(p))

    def list_environments(self) -> list[ListedEnvironment]:
        """The environments in the search paths, in search order."""
        listed = []
        for root in self.search_paths:
            provider_dir = root / self.provider_name
            if not provider_dir.is_dir():
                continue
            read_only = not self.is_install_path(root)
            for directory in sorted(provider_dir.iterdir()):
                if not directory.is_dir():
                    continue
                marker = EnvironmentMarker.read(directory)
                if marker is None and read_only:
                    continue
                listed.append(
                    ListedEnvironment(
                        key=directory.name,
                        name=marker.name if marker else None,
                        path=directory,
                        read_only=read_only,
                    )
                )
        return listed

    @property
    @abstractmethod
    def provider_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def environment_key(self, spec: EnvironmentSpec) -> str:
        """
        Return a unique deterministic key for the given environment specification.
        This is used to determine if an environment already exists.
        """
        raise NotImplementedError

    @abstractmethod
    def ensure_environment(self, spec: EnvironmentSpec) -> EnvironmentHandle:
        """
        Ensure that an environment matching the given specification exists, and return a handle to it.
        If the environment already exists, it should be reused. If it does not exist, it should be created.
        """
        raise NotImplementedError

    @abstractmethod
    def resolve_environment(self, spec: EnvironmentSpec) -> EnvironmentResolutionResult:
        """
        Resolve an environment specification without creating the environment.
        """
        raise NotImplementedError

    @abstractmethod
    def inspect_environment(self, handle: EnvironmentHandle) -> EnvironmentInfo:
        raise NotImplementedError

    def build_provenance(
        self,
        spec: EnvironmentSpec,
        handle: EnvironmentHandle | None = None,
    ) -> EnvironmentProvenance:
        return EnvironmentProvenance(
            provider=self.provider_name,
            key=self.environment_key(spec),
            path=handle.path.as_posix() if handle and handle.path else None,
            spec_hash=spec.hash(),
            python=spec.python,
            requirements=spec.requirements,
            provider_requirements=spec.provider_requirements,
        )

    @abstractmethod
    def remove_environment(self, handle: EnvironmentHandle) -> None:
        raise NotImplementedError
