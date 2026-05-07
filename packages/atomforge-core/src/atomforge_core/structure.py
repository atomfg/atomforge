from typing import Any

from pydantic import BaseModel, field_validator, model_validator, Field

class StructureData(BaseModel):
    """
    A Pydantic model for serializing and deserializing Structure data.
    """

    positions: list[list[float]] = Field(..., description="List of atomic positions, where each position is a list of three floats. Coordinates are in Angstroms.")
    cell: list[list[float]] = Field(..., description="List of three lattice vectors, each containing three floats. Coordinates are in Angstroms.")
    numbers: list[int] = Field(..., description="List of atomic numbers corresponding to each position.")
    pbc: list[bool, bool, bool] = Field(..., description="Periodic boundary conditions in each direction.")

    spin_multiplicity: int | None = Field(None, description="Spin multiplicity of the structure, if applicable. Not all models will meaningfully use this field.")
    charge: int | None = Field(None, description="Total charge of the structure, if applicable. Not all models will meaningfully use this field.")

    @field_validator('positions')
    def validate_positions(cls, value):
        if not isinstance(value, list) or not all(isinstance(pos, list) and len(pos) == 3 for pos in value):
            raise ValueError("Positions must be a list of lists, each containing three floats.")
        return value
    
    @field_validator('cell')
    def validate_cell(cls, value):
        if not isinstance(value, list) or len(value) != 3 or not all(isinstance(vec, list) and len(vec) == 3 for vec in value):
            raise ValueError("Cell must be a list of three lists, each containing three floats.")
        return value
    
    @model_validator(mode='after')
    def validate_numbers_and_positions(self):
        if len(self.numbers) != len(self.positions):
            raise ValueError("The length of numbers must match the length of positions.")
        return self
    
    def to_ase_dict(self) -> dict[str, Any]:
        return {
            "positions": self.positions,
            "cell": self.cell,
            "numbers": self.numbers,
            "pbc": self.pbc
        }

