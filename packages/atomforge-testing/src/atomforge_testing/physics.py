"""Tolerances, geometry helpers and deviation measures for the physics checks.

Each deviation function returns a number that `ModelPhysicsContract` compares
with a tolerance. The functions are public so that the same quantities can be
measured outside the contracts, e.g. to choose the default tolerances.

Units follow atomforge: eV, Å, eV/Å and eV/Å³.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import math

from atomforge_core.structure import StructureData


@dataclass(frozen=True)
class ModelPhysics:
    """Physical properties a model has, which the physics checks rely on.

    A model declares in its test case each property it does not have; the
    checks that rely on it are then skipped. Every property is claimed by
    default.

    - ``conservative_forces``: forces (and stress) are derivatives of the
      energy. Direct-force models predict them separately.
    - ``translation_invariant``: the energy does not change under a rigid
      translation.
    - ``rotation_invariant``: the energy does not change under a rigid
      rotation. Models that learn rotational symmetry from data rather than by
      construction are only approximately invariant.

    A check that follows from two properties needs both: zero net force from a
    conservative, translation-invariant model, and symmetric stress from a
    conservative, rotation-invariant one.
    """

    conservative_forces: bool = True
    translation_invariant: bool = True
    rotation_invariant: bool = True

    def missing(self, *properties: str) -> list[str]:
        """Those of ``properties`` the model declares it does not have."""
        return [name for name in properties if not getattr(self, name)]


@dataclass(frozen=True)
class Tolerances:
    """Absolute tolerances for one precision.

    - ``energy_per_atom``: energy differences, divided by the number of atoms
      (eV/atom).
    - ``forces``: force differences, per component (eV/Å). The net force check
      compares the net force divided by the number of atoms.
    - ``stress``: stress differences, per component (eV/Å³).
    - ``finite_difference``: largest difference between a force component and
      minus the central finite difference of the energy (eV/Å).
    - ``finite_difference_step``: displacement used for that finite
      difference (Å).
    """

    energy_per_atom: float
    forces: float
    stress: float
    finite_difference: float
    finite_difference_step: float


# Measured: ten times the largest deviation observed on the existing plugins
# and the reference structures, rounded up to 1 or 3 x 10^n. See the research
# post "Default tolerances for the atomforge-testing physics checks" in the
# workspace blog. The f64 stress tolerance has no measurement behind it (only
# orb computes f64 stress, and orb declares itself not rotation invariant); it
# keeps the ratio between the f32 stress and energy tolerances.
DEFAULT_TOLERANCES: Mapping[str, Tolerances] = {
    "f32": Tolerances(
        energy_per_atom=1e-5,
        forces=1e-4,
        stress=1e-7,
        finite_difference=3e-2,
        finite_difference_step=3e-3,
    ),
    "f64": Tolerances(
        energy_per_atom=1e-14,
        forces=1e-13,
        stress=1e-16,
        finite_difference=1e-5,
        finite_difference_step=1e-4,
    ),
}


def tolerance_key(precision: str | None) -> str:
    """The tolerance set for a requested precision. A model that does not use
    the precision knob (``default``) runs at its own precision, which the host
    cannot know; it gets the looser ``f32`` set."""
    return "f64" if precision == "f64" else "f32"


def tolerances_for(
    precision: str | None, overrides: Mapping[str, Tolerances] | None = None
) -> Tolerances:
    key = tolerance_key(precision)
    if overrides is not None and key in overrides:
        return overrides[key]
    return DEFAULT_TOLERANCES[key]


# Geometry


def _with_positions(
    structure: StructureData, positions: list[list[float]]
) -> StructureData:
    return structure.model_copy(update={"positions": positions})


def translated(structure: StructureData, vector: Sequence[float]) -> StructureData:
    return _with_positions(
        structure,
        [[p[k] + vector[k] for k in range(3)] for p in structure.positions],
    )


def rotated(
    structure: StructureData, axis: Sequence[float], angle_degrees: float
) -> StructureData:
    """Rigid rotation of the positions about their centroid (Rodrigues'
    formula). The cell is not rotated: use it on non-periodic structures."""
    norm = math.sqrt(sum(a * a for a in axis))
    u = [a / norm for a in axis]
    theta = math.radians(angle_degrees)
    c, s = math.cos(theta), math.sin(theta)
    n_atoms = len(structure.positions)
    centroid = [sum(p[k] for p in structure.positions) / n_atoms for k in range(3)]
    rotated_positions = []
    for p in structure.positions:
        v = [p[k] - centroid[k] for k in range(3)]
        dot = sum(u[k] * v[k] for k in range(3))
        cross = [
            u[1] * v[2] - u[2] * v[1],
            u[2] * v[0] - u[0] * v[2],
            u[0] * v[1] - u[1] * v[0],
        ]
        rotated_positions.append(
            [
                centroid[k] + v[k] * c + cross[k] * s + u[k] * dot * (1 - c)
                for k in range(3)
            ]
        )
    return _with_positions(structure, rotated_positions)


def displaced(
    structure: StructureData, atom: int, axis: int, delta: float
) -> StructureData:
    positions = [list(p) for p in structure.positions]
    positions[atom][axis] += delta
    return _with_positions(structure, positions)


# A finite-difference check only tells a right force from a wrong one if the
# force is large against the tolerance: a wrong sign changes the difference by
# twice the force.
INFORMATIVE_FACTOR = 10.0


def largest_force_coordinates(
    forces: Sequence[Sequence[float]], count: int = 3
) -> list[tuple[int, int]]:
    """The (atom, axis) pairs of the ``count`` largest force components, by
    magnitude, largest first."""
    pairs = [(atom, axis) for atom in range(len(forces)) for axis in range(3)]
    pairs.sort(key=lambda pair: -abs(forces[pair[0]][pair[1]]))
    return pairs[:count]


# Deviations


def energy_per_atom_difference(first: float, second: float, n_atoms: int) -> float:
    return abs(first - second) / n_atoms


def max_abs_difference(
    first: Sequence[Sequence[float]], second: Sequence[Sequence[float]]
) -> float:
    return max(
        abs(a - b) for row_a, row_b in zip(first, second) for a, b in zip(row_a, row_b)
    )


def net_force_per_atom(forces: Sequence[Sequence[float]]) -> float:
    """Largest component of the net force, divided by the number of atoms."""
    return max(abs(sum(f[k] for f in forces)) for k in range(3)) / len(forces)


def central_difference_force(
    energy_plus: float, energy_minus: float, step: float
) -> float:
    """Minus the central finite difference of the energy."""
    return -(energy_plus - energy_minus) / (2 * step)


def per_atom_energies_deviation(energies: Sequence[float], energy: float) -> float:
    return abs(sum(energies) - energy) / len(energies)


def stress_asymmetry(stress: Sequence[Sequence[float]]) -> float:
    return max(abs(stress[i][j] - stress[j][i]) for i in range(3) for j in range(3))
