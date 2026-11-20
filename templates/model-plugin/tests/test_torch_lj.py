"""Checks of the model's numbers, run through atomforge in the worker environment.

The host test environment has no torch, so the model is always called through a
backend, just as users call it: `atomforge_backend` is one backend shared by the
whole test session. Replace the reference values with ones for your model, e.g.
computed with the model's own package.

    uv run pytest --atomforge-runtime
    uv run pytest --atomforge-runtime --atomforge-cuda
    uv run pytest --atomforge-runtime --atomforge-mps
"""

import pytest

from atomforge_core.property import Property
from atomforge_core.resources.resource_models import ExecutionResources
from atomforge_core.structure import StructureData

from atomforge_template.spec import TorchLJ

pytestmark = pytest.mark.atomforge_runtime

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


def single_point(backend, structure, resources):
    from atomforge_builtins.task.single_point import SinglePoint

    task = SinglePoint(
        structure=structure, properties=frozenset({Property.ENERGY, Property.FORCES})
    )
    model = TorchLJ(epsilon=EPSILON, sigma=SIGMA)
    return backend.execute(task, model=model, exec_resources=resources)


def cpu(precision: str) -> ExecutionResources:
    return ExecutionResources(accelerator="cpu", precision=precision, strict=True)


def test_dimer_matches_analytic_lj(atomforge_backend):
    result = single_point(atomforge_backend, dimer(DISTANCE), cpu("f64"))

    assert result.energy == pytest.approx(lj_dimer_energy(DISTANCE), rel=1e-12)
    force = lj_dimer_force(DISTANCE)
    assert result.forces == [
        pytest.approx([-force, 0.0, 0.0], abs=1e-12),
        pytest.approx([force, 0.0, 0.0], abs=1e-12),
    ]


def test_forces_sum_to_zero(atomforge_backend):
    result = single_point(atomforge_backend, trimer(), cpu("f64"))

    total = [sum(force[k] for force in result.forces) for k in range(3)]
    assert total == pytest.approx([0.0, 0.0, 0.0], abs=1e-12)


def test_f32_agrees_with_f64(atomforge_backend):
    f64 = single_point(atomforge_backend, trimer(), cpu("f64"))
    f32 = single_point(atomforge_backend, trimer(), cpu("f32"))

    assert f32.energy == pytest.approx(f64.energy, rel=1e-5)


@pytest.mark.atomforge_cuda
def test_cuda_agrees_with_cpu(atomforge_backend):
    cuda = ExecutionResources(accelerator="cuda", precision="f64", strict=True)
    on_cuda = single_point(atomforge_backend, trimer(), cuda)
    on_cpu = single_point(atomforge_backend, trimer(), cpu("f64"))

    assert on_cuda.energy == pytest.approx(on_cpu.energy, rel=1e-10)
    for cuda_force, cpu_force in zip(on_cuda.forces, on_cpu.forces):
        assert cuda_force == pytest.approx(cpu_force, abs=1e-10)


@pytest.mark.atomforge_mps
def test_mps_agrees_with_cpu_in_f32(atomforge_backend):
    mps = ExecutionResources(accelerator="mps", precision="f32", strict=True)
    on_mps = single_point(atomforge_backend, trimer(), mps)
    on_cpu = single_point(atomforge_backend, trimer(), cpu("f32"))

    assert on_mps.energy == pytest.approx(on_cpu.energy, rel=1e-5)
    for mps_force, cpu_force in zip(on_mps.forces, on_cpu.forces):
        assert mps_force == pytest.approx(cpu_force, rel=1e-4, abs=1e-5)
