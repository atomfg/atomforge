import subprocess
from pathlib import Path

from atomforge.env.base.env import EnvironmentHandle, EnvironmentInfo, EnvironmentSpec
from atomforge.env.base.provider import EnvironmentProvider


class UVEnvironmentProvider(EnvironmentProvider):
    provider_name = "uv"

    def __init__(self, search_path: tuple[Path, ...], install_path: Path):
        super().__init__(search_path, install_path)

    def _install_requirements(
        self, env_path: Path, requirements: tuple[str, ...]
    ) -> None:
        command = [
            "uv",
            "-q",
            "pip",
            "install",
            "-p",
            env_path.as_posix(),
            "-r",
            "-",
        ]

        requirements_str = "\n".join(requirements)
        subprocess.run(command, input=requirements_str.encode(), check=True)

    def _install_providers(
        self, env_path: Path, provider_requirements: tuple[str, ...]
    ) -> None:
        self._install_requirements(env_path, provider_requirements)

    def _install_atomforge(self, env_path: Path) -> None:
        command = [
            "uv",
            "-q",
            "pip",
            "install",
            "-p",
            env_path.as_posix(),
            "-P",
            "atomforge",
            f"atomforge @ {Path(__file__).parent.parent.parent.parent.as_posix()}",
        ]

        subprocess.run(command, check=True)

    def search_for_environment(self, env_name: str) -> EnvironmentHandle | None:
        for env_path in self.search_paths:
            candidate = env_path / env_name
            if candidate.exists():
                return EnvironmentHandle(
                    name=env_name, provider=self.provider_name, path=candidate
                )
        return None

    def ensure_environment(self, spec: EnvironmentSpec) -> EnvironmentHandle:
        # Look for an existing environment matching the spec.
        # For simplicity, we just use the short hash of the spec as the environment name.

        env_name = spec.short_hash()
        existing_env = self.search_for_environment(env_name)
        if existing_env:
            return existing_env

        env_path = (self.install_path / env_name).resolve()

        if not env_path.exists():
            command = ["uv", "-q", "venv", env_path.as_posix()]
            if spec.python:
                command.extend(["--python", spec.python])
            subprocess.run(command, check=True)

        # Install requirements
        if spec.requirements:
            self._install_requirements(env_path, spec.requirements)

        # Install provider requirements for entry-point / plugin discovery.
        if spec.provider_requirements:
            self._install_providers(env_path, spec.provider_requirements)

        # Install atomforge itself, ensuring that the backend code is available in the environment.
        self._install_atomforge(env_path)

        # Return a handle to the environment
        return EnvironmentHandle(
            name=spec.name, provider=self.provider_name, path=env_path
        )

    def inspect_environment(self, handle: EnvironmentHandle) -> EnvironmentInfo:
        env_path = handle.path
        python_executable = env_path / "bin" / "python"
        exists = env_path.exists() and python_executable.exists()
        return EnvironmentInfo(
            handle=handle,
            path=env_path,
            python_executable=python_executable if exists else None,
            exists=exists,
        )

    def remove_environment(self, handle: EnvironmentHandle) -> None:
        env_path = handle.path
        if env_path.exists():
            subprocess.run(["rm", "-rf", env_path.as_posix()], check=True)
