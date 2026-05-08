from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


WHEEL_PATTERNS = [
    "packages/atomforge-core/dist/*.whl",
    "packages/atomforge-runtime/dist/*.whl",
    "packages/atomforge-builtins/dist/*.whl",
    "packages/atomforge-testing/dist/*.whl",
    "dist/*.whl",
]


SMOKE_IMPORTS = """
import importlib.metadata as metadata

import atomforge
import atomforge_builtins
import atomforge_core
import atomforge_runtime
import atomforge_testing

task_names = {entry_point.name for entry_point in metadata.entry_points(group="atomforge.task")}
model_names = {entry_point.name for entry_point in metadata.entry_points(group="atomforge.model")}
missing_tasks = {"single_point", "bfgs", "optimize", "analyze_symmetry", "atomic_descriptor"} - task_names
missing_models = {"lennard_jones", "no_dep"} - model_names
if missing_tasks or missing_models:
    raise SystemExit(
        f"Missing entry points: tasks={sorted(missing_tasks)}, models={sorted(missing_models)}"
    )
"""


def built_wheels() -> list[Path]:
    wheels: list[Path] = []
    for pattern in WHEEL_PATTERNS:
        matches = sorted(Path().glob(pattern))
        if len(matches) != 1:
            raise SystemExit(f"Expected exactly one built wheel for {pattern}, found {len(matches)}.")
        wheels.extend(matches)
    return wheels


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def main() -> int:
    wheels = built_wheels()
    uv = shutil.which("uv")
    if uv is None:
        raise SystemExit("uv is required for release smoke tests.")

    with tempfile.TemporaryDirectory() as tmpdir:
        venv = Path(tmpdir) / "venv"
        run([uv, "venv", "--python", "3.13", str(venv)])
        python = venv / "bin" / "python"
        atomforge = venv / "bin" / "atomforge"
        run([uv, "pip", "install", "--python", str(python), *(str(wheel) for wheel in wheels)])
        run([str(atomforge), "--help"])
        run([str(python), "-c", SMOKE_IMPORTS])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
