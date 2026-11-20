"""Acceptance tests for "Model results as float64 arrays, design" in the
engineering log: the declared types of ModelResult name numpy arrays, but
atomforge-core does not import numpy."""

import dataclasses
import subprocess
import sys

from atomforge_core.model.result import ModelResult


def test_importing_model_result_does_not_import_numpy():
    code = (
        "import sys\n"
        "import atomforge_core.model.result\n"
        "assert 'numpy' not in sys.modules, 'numpy was imported'\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True
    )
    assert completed.returncode == 0, completed.stderr


def _annotation(name: str) -> str:
    (field,) = [f for f in dataclasses.fields(ModelResult) if f.name == name]
    return str(field.type)


def test_energy_is_declared_a_float():
    assert _annotation("energy") == "float | None"


def test_array_fields_are_declared_float64_arrays():
    declared = {
        name: _annotation(name) for name in ("forces", "stress", "energies", "magmoms")
    }
    assert declared == {
        name: "NDArray[np.float64] | None"
        for name in ("forces", "stress", "energies", "magmoms")
    }
