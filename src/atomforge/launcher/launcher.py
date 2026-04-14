from atomforge.env import EnvironmentHandle, EnvironmentSpec, UVEnvironmentProvider
import subprocess


class Launcher:
    def __init__(self):
        pass

    def run(self, command: list[str], env_handle: EnvironmentHandle) -> int:
        """
        Run the given command in the environment specified by env_handle.
        """
        env_info = UVEnvironmentProvider().inspect_environment(env_handle)

        if not env_info.exists:
            raise ValueError(f"Environment {env_handle.name} does not exist")

        command = [env_info.python_executable.as_posix()] + command
        result = subprocess.run(command)
        return result.returncode


if __name__ == "__main__":
    from rich import print

    provider = UVEnvironmentProvider()

    spec = EnvironmentSpec(
        name="test-env", python="python3.10", requirements=["requests", "numpy", "ase"]
    )
    handle = provider.ensure_environment(spec)

    launcher = Launcher()
    return_code = launcher.run(
        [
            "-c",
            "import requests; print(requests.__version__); import numpy; print(numpy.__version__); import ase; print(ase.__version__)",
        ],
        handle,
    )
    print(f"Command exited with code {return_code}")
