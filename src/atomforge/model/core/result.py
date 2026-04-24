from dataclasses import dataclass, field

@dataclass(slots=True)
class ModelResult:
    energy: float | None = None
    forces: list[list[float]] | None = None
    stress: list[list[float]] | None = None
    extras: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, str] = field(default_factory=dict)
