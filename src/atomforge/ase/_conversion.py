from __future__ import annotations

from typing import TYPE_CHECKING

from atomforge_core.structure import StructureData

if TYPE_CHECKING:
    from ase import Atoms

CHARGE_KEY = "charge"
SPIN_KEY = "spin"


def atoms_to_structure(atoms: Atoms) -> StructureData:
    """Convert an ``ase.Atoms`` object to ``StructureData``.

    Total charge and spin multiplicity are read from ``atoms.info["charge"]``
    and ``atoms.info["spin"]`` when present (the same convention as fairchem).
    Per-atom ``initial_charges`` and ``initial_magmoms`` are not transferred.
    """
    return StructureData(
        positions=atoms.get_positions().tolist(),
        cell=atoms.cell[:].tolist(),
        numbers=atoms.get_atomic_numbers().tolist(),
        pbc=[bool(p) for p in atoms.pbc],
        charge=atoms.info.get(CHARGE_KEY),
        spin_multiplicity=atoms.info.get(SPIN_KEY),
    )
