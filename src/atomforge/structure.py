from dataclasses import dataclass
from typing import Self
from pydantic import BaseModel
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
    
    def to_message(self) -> "StructureMessage":
        """
        Convert this Structure to a StructureMessage for serialization.
        """
        return StructureMessage.from_structure(self)
    
class StructureMessage(BaseModel):
    """
    A Pydantic model for serializing and deserializing Structure data.
    """
    positions: list[list[float]]
    cell: list[list[float]]
    species: list[str]
    pbc: list[bool, bool, bool]

    @classmethod
    def from_structure(cls, structure: Structure) -> Self:
        return cls(
            positions=structure.positions.tolist(),
            cell=structure.cell.tolist(),
            species=structure.species,
            pbc=structure.pbc,
        )
    
    def to_structure(self) -> Structure:
        return Structure(
            positions=np.array(self.positions),
            cell=np.array(self.cell),
            species=self.species,
            pbc=self.pbc,
        )