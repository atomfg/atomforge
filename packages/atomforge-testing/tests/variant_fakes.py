"""Fakes for the acceptance tests of "Variants, settings and local weights in
the spec, design": specs with variants, `variant_info` callables, a model
that loads local weights, and factories that write them.

Kept apart from ``testing_fakes`` so the other contract tests do not depend
on the new spec API.
"""

from pathlib import Path
from typing import Annotated, Literal

from pydantic import model_validator

from atomforge_core.model.executor import ModelExecutor
from atomforge_core.model.metadata import VariantInfo
from atomforge_core.model.spec import ModelSpec, Setting, Variant
from atomforge_core.model.weights import LocalWeights

from testing_fakes import InProcessBackend, spring_result

# Specs


class ThreeVariantModel(ModelSpec):
    kind: Literal["fake-model"] = "fake-model"
    environment_profile: Literal["tested"] = "tested"
    model: Annotated[Literal["a", "b", "c"], Variant] = "a"
    scale: Annotated[float, Setting] = 1.0


class DuplicateNamesModel(ModelSpec):
    kind: Literal["fake-model"] = "fake-model"
    model: Annotated[Literal["a", "b"], Variant] = "a"

    @property
    def variant_name(self) -> str:
        return "dup-name"


class DefaultNotCanonicalModel(ModelSpec):
    """Brings `cutoff` to None for `omol` only when `training_data` is given,
    so the default spec (`omol`, `inf`) is not one of the generated
    variants."""

    kind: Literal["fake-model"] = "fake-model"
    cutoff: Annotated[Literal["inf", "20"] | None, Variant] = "inf"
    training_data: Annotated[Literal["omat", "omol"], Variant] = "omol"

    @model_validator(mode="before")
    @classmethod
    def canonical_cutoff(cls, data):
        if isinstance(data, dict) and data.get("training_data") == "omol":
            data = {**data, "cutoff": None}
        return data


class WeightedModel(ModelSpec):
    kind: Literal["fake-model"] = "fake-model"
    model: Annotated[Literal["a", "b"], Variant] = "a"
    weights: LocalWeights | None = None


# variant_info callables for ThreeVariantModel


def good_variant_info(spec) -> VariantInfo:
    return VariantInfo(
        training_data=("FakeSet",),
        level_of_theory="PBE",
        checkpoint=f"ckpt-{spec.model}",
    )


def shared_checkpoint_variant_info(spec) -> VariantInfo:
    return VariantInfo(checkpoint="ckpt-shared")


def incomplete_variant_info(spec) -> VariantInfo:
    if spec.model == "b":
        raise KeyError(spec.model)
    return VariantInfo(checkpoint=f"ckpt-{spec.model}")


# Execution

# Energy per atom added by each variant's trained parameters.
SHIFTS = {"a": 0.0, "b": 1.0, "c": 2.0}


class VariantSpringExecutor(ModelExecutor):
    """The spring model shifted per variant, or by the value stored in the
    local weights file when the spec has one."""

    def compute(self, structure, properties):
        result = spring_result(structure, properties)
        weights = getattr(self.spec, "weights", None)
        if weights is not None:
            shift = float(Path(weights.path).read_text())
        else:
            shift = SHIFTS[getattr(self.spec, "model", "a")]
        if result.energy is not None:
            result.energy += shift * len(structure.numbers)
        return result


def faithful_weights(spec, directory: Path) -> LocalWeights:
    """Writes the variant's own parameters."""
    path = Path(directory) / f"{spec.model}.weights"
    path.write_text(str(SHIFTS[spec.model]))
    return LocalWeights(path)


def wrong_weights(spec, directory: Path) -> LocalWeights:
    """Writes parameters that are not the variant's."""
    path = Path(directory) / f"{spec.model}.weights"
    path.write_text("5.0")
    return LocalWeights(path)


class VerifyingInProcessBackend(InProcessBackend):
    """Checks local weights before running, as the worker does."""

    def execute(self, task, model=None, exec_resources=None, timeout=None):
        if model is not None and getattr(model, "weights", None) is not None:
            model.weights.verify()
        return super().execute(task, model, exec_resources, timeout)


# Declarations that differ between the variants of ThreeVariantModel: "c"
# has no stress and no f64.


def per_variant_properties(spec):
    from atomforge_core.property import Property

    if spec.model == "c":
        return frozenset({Property.ENERGY, Property.FORCES})
    return frozenset({Property.ENERGY, Property.FORCES, Property.STRESS})


def per_variant_capabilities(spec):
    from atomforge_core.resources.resource_caps import ResourceCapabilities

    precisions = ["f32"] if spec.model == "c" else ["f32", "f64"]
    return ResourceCapabilities(accelerator=["cpu"], precision={"cpu": precisions})


def broken_for_c_capabilities(spec):
    if spec.model == "c":
        return {"cpu": ["f32"]}
    return per_variant_capabilities(spec)
