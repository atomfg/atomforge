"""Checks of the model's numbers, run through atomforge in the worker environment.

The host test environment has no torch, so the model is always called through a
backend, just as users call it. Replace the reference values with ones for your
model, e.g. computed with the model's own package.

    ATOMFORGE_RUN_RUNTIME_TESTS=1 uv run pytest -m atomforge_runtime
    ATOMFORGE_RUN_RUNTIME_TESTS=1 ATOMFORGE_TEST_GPU=1 uv run pytest -m atomforge_runtime
"""

import os

import pytest

from atomforge_core.property import Property
from atomforge_core.resources.resource_models import ExecutionResources
from atomforge_core.structure import StructureData

from atomforge_template.spec import TorchLJ

pytestmark = [
    pytest.mark.atomforge_runtime,
    pytest.mark.skipif(
        os.environ.get("ATOMFORGE_RUN_RUNTIME_TESTS") != "1",
        reason="Set ATOMFORGE_RUN_RUNTIME_TESTS=1 to run the model",
    ),
]

EPSILON = 0.5
SIGMA = 2.0
DISTANCE = 2.5
BOX = [[20.0, 0.0, 0.0], [0.0, 20.0, 0.0], [0.0, 0.0, 20.0]]


def dimer(distance: float) -> StructureData:
    return StructureData(
        positions=[[5.0, 5.0, 5.0], [5.0 + distance, 5.0, 5.0]],
        numbers=[18, 18],
        cell=BOX,
        pbc=[False, False, False],
    )


def trimer() -> StructureData:
    return StructureData(
        positions=[[5.0, 5.0, 5.0], [7.3, 5.0, 5.0], [6.0, 7.1, 5.4]],
        numbers=[18, 18, 18],
        cell=BOX,
        pbc=[False, False, False],
    )


def lj_dimer_energy(r: float) -> float:
    sr6 = (SIGMA / r) ** 6
    return 4 * EPSILON * (sr6**2 - sr6)


def lj_dimer_force(r: float) -> float:
    """Force on the second atom along the bond, -dE/dr."""
    sr6 = (SIGMA / r) ** 6
    return 24 * EPSILON * (2 * sr6**2 - sr6) / r


@pytest.fixture(scope="module")
def backend():
    from atomforge.backend.subprocess import SubprocessBackend

    with SubprocessBackend() as backend:
        yield backend


def single_point(backend, structure, resources):
    from atomforge_builtins.task.single_point import SinglePoint

    task = SinglePoint(
        structure=structure, properties=frozenset({Property.ENERGY, Property.FORCES})
    )
    model = TorchLJ(epsilon=EPSILON, sigma=SIGMA)
    return backend.execute(task, model=model, exec_resources=resources)


def cpu(precision: str) -> ExecutionResources:
    return ExecutionResources(accelerator="cpu", precision=precision, strict=True)


def test_dimer_matches_analytic_lj(backend):
    result = single_point(backend, dimer(DISTANCE), cpu("f64"))

    assert result.energy == pytest.approx(lj_dimer_energy(DISTANCE), rel=1e-12)
    force = lj_dimer_force(DISTANCE)
    assert result.forces == [
        pytest.approx([-force, 0.0, 0.0], abs=1e-12),
        pytest.approx([force, 0.0, 0.0], abs=1e-12),
    ]


def test_forces_sum_to_zero(backend):
    result = single_point(backend, trimer(), cpu("f64"))

    total = [sum(force[k] for force in result.forces) for k in range(3)]
    assert total == pytest.approx([0.0, 0.0, 0.0], abs=1e-12)


def test_f32_agrees_with_f64(backend):
    f64 = single_point(backend, trimer(), cpu("f64"))
    f32 = single_point(backend, trimer(), cpu("f32"))

    assert f32.energy == pytest.approx(f64.energy, rel=1e-5)


@pytest.mark.skipif(
    os.environ.get("ATOMFORGE_TEST_GPU") != "1",
    reason="Set ATOMFORGE_TEST_GPU=1 on a machine with a CUDA GPU",
)
def test_gpu_agrees_with_cpu(backend):
    gpu = ExecutionResources(accelerator="gpu", precision="f64", strict=True)
    on_gpu = single_point(backend, trimer(), gpu)
    on_cpu = single_point(backend, trimer(), cpu("f64"))

    assert on_gpu.energy == pytest.approx(on_cpu.energy, rel=1e-10)
    for gpu_force, cpu_force in zip(on_gpu.forces, on_cpu.forces):
        assert gpu_force == pytest.approx(cpu_force, abs=1e-10)
