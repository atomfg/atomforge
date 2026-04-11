from dataclasses import dataclass
import numpy as np

@dataclass(slots=True)
class Structure:
    """
    A simple data class representing an atomic structure. 
    """
    positions: np.ndarray
    cell: np.ndarray
    species: list[str]
    pbc: list[bool, bool, bool]

    @classmethod
    def from_ase(cls, atoms):
        """
        Create a Structure from an ASE Atoms object.
        """
        return cls(
            positions=atoms.get_positions(),
            cell=atoms.get_cell().array,
            species=atoms.get_chemical_symbols(),
            pbc=atoms.get_pbc(),
        )
    
    def to_ase(self):
        """
        Convert this Structure to an ASE Atoms object.
        """
        from ase import Atoms
        return Atoms(
            symbols=self.species,
            positions=self.positions,
            cell=self.cell,
            pbc=self.pbc,
        )