from abc import ABC, abstractmethod
from .env import EnvironmentSpec, EnvironmentHandle, EnvironmentInfo

from pathlib import Path

class EnvironmentProvider(ABC):

    def __init__(self, root_path: Path | str | None = None):
        self.root_path = Path(root_path) if root_path else Path.home() / ".atomforge" / "envs"
        self.root_path.mkdir(parents=True, exist_ok=True)

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
