from pathlib import Path
from typing import Mapping

from atomforge.env.base.dependency import ResolvedDependency

# Every worker project has this name. uv refuses a project that depends on a
# package of its own name, so the environment's name (a display name, which a
# plugin may set to its package's name) is kept in a comment instead.
WORKER_PROJECT_NAME = "atomforge-worker"

pyproject_template = """# atomforge environment: {env_name}
[project]
name = "{project_name}"
version = "0.1.0"
description = "Add your description here"
requires-python = "{python_spec}"
dependencies = [{dependencies}]

{extras}
"""


class PyprojectWriter:
    def __init__(
        self,
        env_name: str,
        python_version: str | None,
        dependencies: list[ResolvedDependency],
        extras: Mapping[str, str] | None = None,
    ):
        self.env_name = env_name
        self.python_version = python_version
        self.dependencies = dependencies
        self.extras = extras or {}

    def _python_string(self) -> str:
        return self.python_version or ">=3.10"

    def _dependency_string(self) -> str:
        return ",\n    ".join([f'"{dep}"' for dep in self.dependencies])

    def _extras_string(self) -> str:
        extras = ""
        return extras

    def to_pyproject(self) -> str:
        # Format dependencies:
        dependencies_str = self._dependency_string()
        python_spec = self._python_string()

        extras = self._extras_string()

        return pyproject_template.format(
            env_name=self.env_name,
            project_name=WORKER_PROJECT_NAME,
            python_spec=python_spec,
            dependencies=dependencies_str,
            extras=extras,
        )

    def write(self, path: Path) -> None:
        pyproject_content = self.to_pyproject()
        path.write_text(pyproject_content)
