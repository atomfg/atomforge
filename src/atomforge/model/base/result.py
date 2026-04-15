from dataclasses import dataclass, field
import numpy as np


@dataclass(slots=True)
class ModelResult:
    energy: float | None = None
    forces: np.ndarray | None = None
    stress: np.ndarray | None = None
    extras: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, str] = field(default_factory=dict)
