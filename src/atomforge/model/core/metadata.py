from dataclasses import dataclass, field
from typing import Any, Mapping, Literal


@dataclass(frozen=True)
class Reference:
    label: str
    url: str
    kind: Literal["repo", "paper", "docs", "homepage"]


@dataclass(frozen=True)
class ModelMetadata:
    id: str
    name: str
    method_family: Literal["empirical", "mlip", "dft"]
    implementation: str | None = None
    references: tuple[Reference, ...] = ()
    tags: frozenset[str] = frozenset()
    extras: Mapping[str, Any] = field(default_factory=dict)
    description: str | None = None