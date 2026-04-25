from abc import ABC, abstractmethod
from atomforge_core.env.env import EnvironmentSpec
from atomforge.env.base.handle import EnvironmentHandle
from atomforge.env.base.info import EnvironmentInfo

from pathlib import Path


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
    def ensure_environment(self, spec: EnvironmentSpec) -> EnvironmentHandle:
        """
        Ensure that an environment matching the given specification exists, and return a handle to it.
        If the environment already exists, it should be reused. If it does not exist, it should be created.
        """
        raise NotImplementedError

    @abstractmethod
    def inspect_environment(self, handle: EnvironmentHandle) -> EnvironmentInfo:
        raise NotImplementedError

    @abstractmethod
    def remove_environment(self, handle: EnvironmentHandle) -> None:
        raise NotImplementedError
