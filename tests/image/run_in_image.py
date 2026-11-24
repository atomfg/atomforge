"""Runs inside the image (see test_image.py): a single point with each model,
with uv taken off PATH, and prints one JSON object with the results.

Usage: python run_in_image.py <weights.json>"""

import json
import logging
import os
import shutil
import sys
from pathlib import Path

# Preloaded environments must be used without running uv.
while (uv := shutil.which("uv")) is not None:
    uv_dir = Path(uv).parent.resolve()
    os.environ["PATH"] = os.pathsep.join(
        p
        for p in os.environ["PATH"].split(os.pathsep)
        if p and Path(p).resolve() != uv_dir
    )

from atomforge.backend.subprocess.backend import SubprocessBackend  # noqa: E402
from atomforge_builtins.model.ase_lj.spec import LennardJones  # noqa: E402
from atomforge_builtins.task.single_point.spec import SinglePoint  # noqa: E402
from atomforge_core.model.weights import LocalWeights  # noqa: E402
from atomforge_core.structure import StructureData  # noqa: E402
from atomforge_template.spec import TorchLJ  # noqa: E402

warnings: list[str] = []


class Collect(logging.Handler):
    def emit(self, record):
        warnings.append(record.getMessage())


handler = Collect(level=logging.WARNING)
logging.getLogger("atomforge").addHandler(handler)

structure = StructureData(
    positions=[[0, 0, 0], [3.8, 0, 0], [0, 3.9, 0]],
    numbers=[18, 18, 18],
    cell=[[10, 0, 0], [0, 10, 0], [0, 0, 10]],
    pbc=[False, False, False],
)
models = {
    "ase-lj": LennardJones(sigma=3.4, epsilon=0.0104),
    "torch-lj": TorchLJ(weights=LocalWeights(sys.argv[1])),
}
results = {}
with SubprocessBackend() as backend:
    for name, model in models.items():
        result = backend.execute(SinglePoint(structure=structure), model)
        results[name] = {
            "energy": float(result.energy),
            "environment_path": result.provenance.environment.path,
        }

print(json.dumps({"results": results, "warnings": warnings}))
