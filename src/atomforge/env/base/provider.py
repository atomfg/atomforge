from abc import ABC, abstractmethod
import hashlib

from atomforge_core.env.env import EnvironmentSpec
from atomforge_core.provenance import EnvironmentProvenance
from atomforge.env.base.handle import EnvironmentHandle
from atomforge.env.base.info import EnvironmentInfo

from pathlib import Path


def file_sha256(path: Path) -> str | None:
    if not path.exists():
        return None

    hasher = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


class EnvironmentProvider(ABC):
    def __init__(self, search_path: tuple[Path, ...], install_path: Path):
        self.install_path = (
            Path(install_path) if install_path else Path.home() / ".atomforge" / "envs"
        )
        self.install_path.mkdir(parents=True, exist_ok=True)

        self.search_paths = tuple(Path(p) for p in search_path if Path(p).exists())
        if self.install_path not in self.search_paths:
            self.search_paths = (self.install_path,) + self.search_paths

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
            spec_hash=spec.hash(),
            python=spec.python,
            requirements=spec.requirements,
            provider_requirements=spec.provider_requirements,
        )

    @abstractmethod
    def remove_environment(self, handle: EnvironmentHandle) -> None:
        raise NotImplementedError
