from __future__ import annotations

from enum import Enum


class Property(str, Enum):
    ENERGY = "energy"
    FORCES = "forces"
    STRESS = "stress"
