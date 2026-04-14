import subprocess
from pathlib import Path

from atomforge.env import (
    EnvironmentHandle,
    EnvironmentInfo,
    EnvironmentProvider,
    EnvironmentSpec,
)


class UVEnvironmentProvider(EnvironmentProvider):
    provider_name = "uv"

    def __init__(self, root_path: Path | str | None = None):
        super().__init__(root_path)

    def ensure_environment(self, spec: EnvironmentSpec) -> EnvironmentHandle:
        # Make the environment
        env_path = (self.root_path / Path(spec.short_hash())).resolve()

        if not env_path.exists():
            command = ["uv", "-q", "venv", env_path.as_posix()]
            if spec.python:
                command.extend(["--python", spec.python])
            subprocess.run(command, check=True)

        # Install requirements
        if spec.requirements:
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

            requirements = "\n".join(spec.requirements)
            subprocess.run(command, input=requirements.encode(), check=True)

        # Install atomforge itself, ensuring that the backend code is available in the environment.
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


if __name__ == "__main__":
    from rich import print

    provider = UVEnvironmentProvider()

    spec1 = EnvironmentSpec(
        name="test-env", python="python3.12", requirements=["requests"]
    )
    spec2 = EnvironmentSpec(
        name="test-env", python="python3.12", requirements=["requests", "numpy"]
    )

    spec = spec2 + spec1

    handle = provider.ensure_environment(spec)

    info = provider.inspect_environment(handle)
    print(info)
    provider.remove_environment(handle)
