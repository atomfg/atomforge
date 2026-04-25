from pathlib import Path
from dataclasses import dataclass

from atomforge_core.task import spec

pyproject_template = """[project]
name = "{env_name}"
version = "0.1.0"
description = "Add your description here"
requires-python = "{python_spec}{python_version}"
dependencies = [{dependencies}]

[tool.uv.sources]
{uv_sources}
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


@dataclass
class PyprojectSpec:
    env_name: str
    python_version: str
    dependencies: list[str]
    uv_sources: dict[str, str]

    def to_pyproject(self) -> str:
        dependencies_str = ",\n\t".join(f'"{dep}"' for dep in self.dependencies)
        uv_sources_str = "\n".join(
            f'{name} = {path}' for name, path in self.uv_sources.items()
        )

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

        return pyproject_template.format(
            env_name=self.env_name,
            python_version=python_version,
            python_spec=python_spec,
            dependencies=dependencies_str,
            uv_sources=uv_sources_str,
        )
    
    def write(self, path: Path) -> None:
        pyproject_content = self.to_pyproject()
        path.write_text(pyproject_content)