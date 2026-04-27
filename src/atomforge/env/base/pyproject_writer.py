from pathlib import Path

from atomforge.env.base.dependency import ResolvedDependency

pyproject_template = """[project]
name = "{env_name}"
version = "0.1.0"
description = "Add your description here"
requires-python = "{python_spec}{python_version}"
dependencies = [{dependencies}]

{extras}
"""

def parse_python(python_str: str) -> tuple[str, str | None]:
    special_characters = ["==", ">=", "<=", "!=", ">", "<", "~=", "@", ";"]
    for char in special_characters:
        if char in python_str:
            break
    else:
        # No special characters found, return just version
        return python_str.strip(), None

    # Split at char
    version = python_str.split(char, 1)[1].strip()
    return version, char

class PyprojectWriter:

    def __init__(self, env_name: str, python_version: str | None, dependencies: list[ResolvedDependency]):
        self.env_name = env_name
        self.python_version = python_version
        self.dependencies = dependencies

    def _python_string(self) -> str:
        # Python
        if self.python_version is None:
            python_version = "3.10"
            python_spec = ">="
        else:
            python_version, python_spec = parse_python(self.python_version)
            if python_spec is None:
                python_spec = "=="

            if len(python_version.split(".")) == 2 and python_spec == "==":
                python_version = python_version + ".*"
            else:
                python_version = python_version

        return python_version, python_spec
    
    def _dependency_string(self) -> str:
        return ",\n    ".join(
            [f'"{dep}"' for dep in self.dependencies]
        )

    def _extras_string(self) -> str:
        extras = ""
        return extras

    def to_pyproject(self) -> str:
        # Format dependencies:
        dependencies_str = self._dependency_string()
        python_version, python_spec = self._python_string()

        extras = self._extras_string()

        return pyproject_template.format(
            env_name=self.env_name,
            python_version=python_version,
            python_spec=python_spec,
            dependencies=dependencies_str,
            extras=extras,
        )
    
    def write(self, path: Path) -> None:
        pyproject_content = self.to_pyproject()
        path.write_text(pyproject_content)