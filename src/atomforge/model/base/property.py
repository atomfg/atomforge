from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import numpy as np


class Property(str, Enum):
    ENERGY = "energy"
    FORCES = "forces"
    STRESS = "stress"


@dataclass(slots=True)
class ModelResult:
    energy: float | None = None
    forces: np.ndarray | None = None
    stress: np.ndarray | None = None
    extras: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, str] = field(default_factory=dict)