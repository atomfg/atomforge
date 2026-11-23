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


@dataclass(frozen=True)
class VariantInfo:
    """Declared facts about one variant of a model kind, from the manifest's
    optional ``variant_info`` callable (``spec -> VariantInfo``). Every field
    is optional."""

    description: str | None = None
    # Datasets the parameters were trained on, e.g. ("OMat24", "sAlex").
    training_data: tuple[str, ...] = ()
    # Reference method of the training labels, e.g. "PBE", "r2SCAN".
    level_of_theory: str | None = None
    # Name or URL of the checkpoint, with its revision where there is one.
    checkpoint: str | None = None
    # Number of trained parameters.
    parameters: int | None = None
