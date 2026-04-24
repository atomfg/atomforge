import ast
import os
from pathlib import Path
import subprocess
import sys

import atomforge
import atomforge.env
import atomforge.model
import atomforge.task
import atomforge.task.core
import atomforge.registry
import atomforge.model.core
import atomforge.registry.model.registry


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src" / "atomforge"
FORBIDDEN_IMPORTS = {
    "atomforge",
    "atomforge.env",
    "atomforge.task",
    "atomforge.model",
    "atomforge.task.core",
    "atomforge.model.core",
}
ALLOWED_FACADE_FILES = {
    SRC_ROOT / "__init__.py",
    SRC_ROOT / "env" / "__init__.py",
    SRC_ROOT / "task" / "__init__.py",
    SRC_ROOT / "task" / "core" / "__init__.py",
    SRC_ROOT / "task" / "registry" / "__init__.py",
    SRC_ROOT / "model" / "__init__.py",
    SRC_ROOT / "model" / "core" / "__init__.py",
}


def _import_targets(node: ast.AST) -> set[str]:
    if isinstance(node, ast.Import):
        return {alias.name for alias in node.names}
    if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module is not None:
        return {node.module}
    return set()


# def test_root_package_exports_only_structure():
#     assert atomforge.__all__ == ["Structure"]
#     assert atomforge.Structure.__name__ == "Structure"
#     assert sorted(name for name in dir(atomforge) if not name.startswith("_")) == [
#         "Structure"
#     ]


def test_public_facades_expose_expected_symbols():
    assert atomforge.env.EnvironmentSpec.__name__ == "EnvironmentSpec"
    assert atomforge.env.UVEnvironmentProvider.__name__ == "UVEnvironmentProvider"
    assert atomforge.task.SinglePoint.__name__ == "SinglePoint"
    assert atomforge.task.BFGS.__name__ == "BFGS"
    assert atomforge.task.core.TaskSpec.__name__ == "TaskSpec"
    assert atomforge.task.core.TaskCapabilitySpec.__name__ == "TaskCapabilitySpec"
    assert atomforge.model.core.ModelSpec.__name__ == "ModelSpec"
    assert atomforge.model.core.Property.__name__ == "Property"
    assert atomforge.registry.model.registry.ModelRegistry.__name__ == "ModelRegistry"


def test_env_facade_does_not_eagerly_import_uv_provider():
    script = """
import atomforge.env
import sys

assert "atomforge.env.uv" not in sys.modules
provider = atomforge.env.UVEnvironmentProvider
assert provider.__name__ == "UVEnvironmentProvider"
assert "atomforge.env.uv" in sys.modules
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_internal_modules_do_not_import_public_facades():
    violations: list[tuple[Path, str]] = []

    for path in SRC_ROOT.rglob("*.py"):
        if path in ALLOWED_FACADE_FILES:
            continue

        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            for target in _import_targets(node):
                if target in FORBIDDEN_IMPORTS:
                    violations.append((path.relative_to(ROOT), target))

    assert violations == []
