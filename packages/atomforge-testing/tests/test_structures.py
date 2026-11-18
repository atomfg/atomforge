"""The reference structures: a molecule, a slab and a bulk crystal near
equilibrium, slightly and reproducibly displaced."""

import math

import pytest

from atomforge_testing import structures

EXPECTED = {
    "molecule": (9, [False, False, False]),
    "slab": (12, [True, True, True]),
    "bulk": (8, [True, True, True]),
}


def test_reference_structures_are_a_molecule_a_slab_and_a_bulk():
    found = structures.reference_structures()

    assert set(found) == set(EXPECTED)
    for name, (n_atoms, pbc) in EXPECTED.items():
        assert len(found[name].numbers) == n_atoms
        assert len(found[name].positions) == n_atoms
        assert list(found[name].pbc) == pbc


def test_reference_structures_are_reproducible():
    assert structures.reference_structures() == structures.reference_structures()


@pytest.mark.parametrize(
    ("factory", "elements"),
    [
        (structures.ethanol, {1, 6, 8}),
        (structures.cu111_slab, {29}),
        (structures.silicon_diamond, {14}),
    ],
)
def test_reference_structure_elements(factory, elements):
    assert set(factory().numbers) == elements


def _min_distance(structure):
    # Minimum image over the periodic directions; the cells are large enough
    # for the neighbouring images to be the only ones that matter.
    cell = structure.cell
    shifts = [
        [sum(n[k] * cell[k][d] for k in range(3)) for d in range(3)]
        for n in (
            (i, j, k)
            for i in ((-1, 0, 1) if structure.pbc[0] else (0,))
            for j in ((-1, 0, 1) if structure.pbc[1] else (0,))
            for k in ((-1, 0, 1) if structure.pbc[2] else (0,))
        )
    ]
    positions = structure.positions
    return min(
        math.dist(positions[a], [positions[b][d] + s[d] for d in range(3)])
        for a in range(len(positions))
        for b in range(len(positions))
        for s in shifts
        if a != b or any(s)
    )


@pytest.mark.parametrize(
    ("factory", "nearest"),
    [
        (structures.ethanol, 0.97),  # O-H bond
        (structures.cu111_slab, 3.61 / math.sqrt(2)),
        (structures.silicon_diamond, 5.43 * math.sqrt(3) / 4),
    ],
)
def test_displacements_keep_the_structure_near_equilibrium(factory, nearest):
    # Each component moves by at most the rattle amplitude, so a distance
    # changes by at most 2 * sqrt(3) times it.
    bound = 2 * math.sqrt(3) * structures.RATTLE_AMPLITUDE

    assert abs(_min_distance(factory()) - nearest) <= bound


def test_every_atom_is_displaced():
    # No atom sits on its ideal site, so no force vanishes by symmetry.
    bulk = structures.silicon_diamond()
    a = bulk.cell[0][0]
    for position in bulk.positions:
        fractional = [4 * x / a for x in position]
        assert any(abs(f - round(f)) > 1e-6 for f in fractional)
