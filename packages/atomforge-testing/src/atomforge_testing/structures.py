import math
import random

from atomforge_core.structure import StructureData


def small_molecule() -> StructureData:
    return StructureData(
        positions=[[4.5, 0.0, 0.0], [5.5, 0.0, 0.0]],
        cell=[[10.0, 0.0, 0.0], [0.0, 10.0, 0.0], [0.0, 0.0, 10.0]],
        numbers=[1, 8],
        pbc=[False, False, False],
    )


def periodic_bulk() -> StructureData:
    return StructureData(
        positions=[
            [0.0, 0.0, 0.0],
            [1.5, 1.5, 1.5],
        ],
        cell=[
            [3.0, 0.0, 0.0],
            [0.0, 3.0, 0.0],
            [0.0, 0.0, 3.0],
        ],
        numbers=[14, 14],
        pbc=[True, True, True],
    )


def isolated_atom() -> StructureData:
    return StructureData(
        positions=[[5.0, 5.0, 5.0]],
        cell=[[10.0, 0.0, 0.0], [0.0, 10.0, 0.0], [0.0, 0.0, 10.0]],
        numbers=[1],
        pbc=[False, False, False],
    )


# Reference structures for the physics checks and the reference regression:
# a molecule, a slab and a bulk crystal near equilibrium, each with every atom
# displaced by a seeded pseudo-random amount so that no force vanishes by
# symmetry. The coordinates are fixed in this module, so the structures do not
# change with an ase release.

RATTLE_AMPLITUDE = 0.05  # Å, largest displacement per Cartesian component
RATTLE_SEED = 7

# Ethanol, CH3CH2OH, in the G2 geometry (Å): C, C, O, then the hydroxyl H and
# the five H on carbon.
_ETHANOL = (
    (6, (1.168181, -0.400382, 0.0)),
    (6, (0.0, 0.559462, 0.0)),
    (8, (-1.190083, -0.227669, 0.0)),
    (1, (-1.946623, 0.381525, 0.0)),
    (1, (0.042557, 1.207508, 0.886933)),
    (1, (0.042557, 1.207508, -0.886933)),
    (1, (2.115891, 0.1448, 0.0)),
    (1, (1.128599, -1.037234, 0.885881)),
    (1, (1.128599, -1.037234, -0.885881)),
)
_ETHANOL_BOX = 12.0

_CU_LATTICE = 3.61  # Å, fcc lattice constant
_CU_VACUUM = 10.0  # Å between the slab and its periodic image

_SI_LATTICE = 5.43  # Å, diamond lattice constant


def _rattled(positions: list[list[float]], seed: int) -> list[list[float]]:
    rng = random.Random(seed)
    return [
        [x + rng.uniform(-RATTLE_AMPLITUDE, RATTLE_AMPLITUDE) for x in position]
        for position in positions
    ]


def ethanol() -> StructureData:
    """Ethanol (9 atoms) in the middle of a 12 Å box, not periodic."""
    centre = _ETHANOL_BOX / 2
    positions = [[centre + x for x in xyz] for _, xyz in _ETHANOL]
    return StructureData(
        positions=_rattled(positions, RATTLE_SEED),
        cell=[
            [_ETHANOL_BOX, 0.0, 0.0],
            [0.0, _ETHANOL_BOX, 0.0],
            [0.0, 0.0, _ETHANOL_BOX],
        ],
        numbers=[number for number, _ in _ETHANOL],
        pbc=[False, False, False],
    )


def cu111_slab() -> StructureData:
    """Cu(111), 2×2 surface cell, 3 layers in ABC stacking (12 atoms).

    Periodic in all three directions, with 10 Å of vacuum between the slab and
    its image along z, so that models which only accept fully periodic
    structures can run it.
    """
    d = _CU_LATTICE / math.sqrt(2)  # nearest-neighbour distance
    spacing = _CU_LATTICE / math.sqrt(3)  # distance between (111) layers
    a1 = (d, 0.0)
    a2 = (d / 2, d * math.sqrt(3) / 2)
    # In-plane offsets of the A, B and C layers, in units of (a1, a2).
    stacking = ((1 / 3, 1 / 3), (2 / 3, 2 / 3), (0.0, 0.0))
    positions = []
    for layer, (f1, f2) in enumerate(stacking):
        for j in range(2):
            for i in range(2):
                u, v = i + f1, j + f2
                positions.append(
                    [
                        u * a1[0] + v * a2[0],
                        u * a1[1] + v * a2[1],
                        _CU_VACUUM / 2 + layer * spacing,
                    ]
                )
    height = 2 * spacing + _CU_VACUUM
    return StructureData(
        positions=_rattled(positions, RATTLE_SEED + 1),
        cell=[[2 * a1[0], 0.0, 0.0], [2 * a2[0], 2 * a2[1], 0.0], [0.0, 0.0, height]],
        numbers=[29] * len(positions),
        pbc=[True, True, True],
    )


def silicon_diamond() -> StructureData:
    """Diamond silicon, conventional cubic cell (8 atoms)."""
    fcc = ((0.0, 0.0, 0.0), (0.0, 0.5, 0.5), (0.5, 0.0, 0.5), (0.5, 0.5, 0.0))
    fractional = [f for site in fcc for f in (site, tuple(c + 0.25 for c in site))]
    positions = [[c * _SI_LATTICE for c in f] for f in fractional]
    return StructureData(
        positions=_rattled(positions, RATTLE_SEED + 2),
        cell=[
            [_SI_LATTICE, 0.0, 0.0],
            [0.0, _SI_LATTICE, 0.0],
            [0.0, 0.0, _SI_LATTICE],
        ],
        numbers=[14] * len(positions),
        pbc=[True, True, True],
    )


def reference_structures() -> dict[str, StructureData]:
    """The molecule, slab and bulk reference structures, by name."""
    return {
        "molecule": ethanol(),
        "slab": cu111_slab(),
        "bulk": silicon_diamond(),
    }
