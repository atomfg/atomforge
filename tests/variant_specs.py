"""Specs for the acceptance tests of "Variants, settings and local weights in
the spec, design": an Orb-like spec with 10 variants, and a spec that takes
local weights. Registered under the ase-lj registration's other symbols."""

from dataclasses import replace
from typing import Annotated, Literal

from pydantic import model_validator

from atomforge_core.model.spec import ModelSpec, Setting, Variant
from atomforge_core.model.weights import LocalWeights


class OrbLike(ModelSpec):
    kind: Literal["orb-like"] = "orb-like"
    force_mode: Annotated[Literal["direct", "conservative"], Variant] = "conservative"
    cutoff: Annotated[Literal["inf", "20"] | None, Variant] = "inf"
    training_data: Annotated[Literal["omat", "mpa", "omol"], Variant] = "omat"
    matmul_precision: Annotated[Literal["highest", "high"], Setting] = "highest"

    @model_validator(mode="before")
    @classmethod
    def canonical_cutoff(cls, data):
        if isinstance(data, dict) and data.get("training_data") == "omol":
            data = {**data, "cutoff": None}
        return data

    @model_validator(mode="after")
    def periodic_models_need_a_cutoff(self):
        if self.training_data != "omol" and self.cutoff is None:
            raise ValueError(f"{self.training_data} needs a cutoff")
        return self


ORB_LIKE_NAMES = {
    f"{force}-{cutoff}-{data}"
    for force in ("direct", "conservative")
    for cutoff in ("inf", "20")
    for data in ("omat", "mpa")
} | {"direct-omol", "conservative-omol"}


class WeightedLike(ModelSpec):
    kind: Literal["weighted-like"] = "weighted-like"
    model: Annotated[Literal["small", "large"], Variant] = "small"
    weights: LocalWeights | None = None


def registrations():
    """The ase-lj registration, and copies of it for the specs above."""
    from atomforge_runtime.registry.model.model_registry import ModelRegistry

    ase_lj = ModelRegistry.default().get("ase-lj")
    return [
        ase_lj,
        replace(ase_lj, kind="orb-like", model_spec=OrbLike),
        replace(ase_lj, kind="weighted-like", model_spec=WeightedLike),
    ]


def registry():
    from atomforge_runtime.registry.model.model_registry import ModelRegistry

    registry = ModelRegistry()
    for registration in registrations():
        registry._register(registration, registration.kind)
    return registry
