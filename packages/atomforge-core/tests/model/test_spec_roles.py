"""Acceptance tests for "Variants, settings and local weights in the spec,
design" in the engineering log: every spec field has a role, and a spec
generates its variants.

`OrbLike` mirrors atomforge-orb's spec: three variant fields, of which
`cutoff` has no effect for `omol` and is brought to `None` there, and one
setting. Its 14 accepted inputs load 10 trained models.
"""

import json
from typing import Annotated, Literal

import pytest
from pydantic import model_validator

from atomforge_core.model.spec import ModelSpec, Setting, Variant
from atomforge_core.model.weights import LocalWeights


class OrbLike(ModelSpec):
    kind: Literal["orb-like"] = "orb-like"
    environment_profile: Literal["tested", "latest"] = "tested"
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


class SingleVariant(ModelSpec):
    kind: Literal["single"] = "single"
    epsilon: Annotated[float, Setting] = 1.0


class Weighted(ModelSpec):
    kind: Literal["weighted"] = "weighted"
    model: Annotated[Literal["small", "large"], Variant] = "small"
    dispersion: Annotated[bool, Setting] = False
    weights: LocalWeights | None = None


@pytest.fixture
def weights_file(tmp_path):
    path = tmp_path / "fine-tuned.model"
    path.write_bytes(b"fine-tuned parameters")
    return path


# Roles


def test_a_field_without_a_role_is_rejected():
    with pytest.raises(TypeError, match="scale"):

        class Unmarked(ModelSpec):
            kind: Literal["unmarked"] = "unmarked"
            scale: float = 1.0


def test_a_field_with_two_roles_is_rejected():
    with pytest.raises(TypeError, match="model"):

        class TwoRoles(ModelSpec):
            kind: Literal["two-roles"] = "two-roles"
            model: Annotated[Literal["a", "b"], Variant, Setting] = "a"


@pytest.mark.parametrize("annotation", [str, int, float])
def test_a_variant_field_that_cannot_be_enumerated_is_rejected(annotation):
    with pytest.raises(TypeError, match="model"):

        class NotEnumerable(ModelSpec):
            kind: Literal["not-enumerable"] = "not-enumerable"
            model: Annotated[annotation, Variant]


def test_bool_and_optional_variant_fields_are_enumerable():
    class Flags(ModelSpec):
        kind: Literal["flags"] = "flags"
        conservative: Annotated[bool, Variant] = True
        head: Annotated[Literal["a"] | None, Variant] = None

    assert len(Flags.variants()) == 4


def test_kind_environment_profile_and_weights_need_no_marker():
    # The classes above define these without markers and import.
    assert "weights" in Weighted.model_fields
    assert "environment_profile" in OrbLike.model_fields


# Generated variants


def test_variants_are_one_per_trained_model():
    variants = OrbLike.variants()

    assert all(isinstance(v, OrbLike) for v in variants)
    assert len(variants) == 10
    assert {v.variant_name for v in variants} == ORB_LIKE_NAMES


def test_accepted_inputs_map_onto_the_variants():
    accepted = []
    for force in ("direct", "conservative"):
        for data in ("omat", "mpa", "omol"):
            for cutoff in ("inf", "20", None):
                try:
                    accepted.append(
                        OrbLike(force_mode=force, training_data=data, cutoff=cutoff)
                    )
                except ValueError:
                    pass

    assert len(accepted) == 14
    assert {spec.variant_name for spec in accepted} == ORB_LIKE_NAMES


def test_variants_have_default_settings():
    assert {v.matmul_precision for v in OrbLike.variants()} == {"highest"}
    assert {v.environment_profile for v in OrbLike.variants()} == {"tested"}


def test_the_default_spec_is_a_variant():
    assert OrbLike().variant_name == "conservative-inf-omat"
    assert OrbLike() in OrbLike.variants()


def test_a_spec_without_variant_fields_has_one_variant_named_default():
    (variant,) = SingleVariant.variants()

    assert variant == SingleVariant()
    assert variant.variant_name == "default"
    assert variant.variant_id == "single/default"


def test_variant_id_is_kind_and_name():
    spec = OrbLike(training_data="omol", force_mode="direct")

    assert spec.variant_id == "orb-like/direct-omol"


def test_settings_do_not_change_the_variant():
    spec = OrbLike(matmul_precision="high", environment_profile="latest")

    assert spec.variant_name == OrbLike().variant_name


def test_a_plugin_may_name_its_variants():
    class Named(ModelSpec):
        kind: Literal["named"] = "named"
        model: Annotated[Literal["s", "l"], Variant] = "s"

        @property
        def variant_name(self) -> str:
            return {"s": "small", "l": "large"}[self.model]

    assert {v.variant_name for v in Named.variants()} == {"small", "large"}
    assert Named().variant_id == "named/small"


def test_variants_have_no_local_weights():
    assert {v.weights for v in Weighted.variants()} == {None}


# Payloads


def test_variant_and_settings_payloads_partition_the_fields():
    spec = OrbLike()
    variant = spec.variant_payload()
    settings = spec.settings_payload()

    assert variant == {
        "force_mode": "conservative",
        "cutoff": "inf",
        "training_data": "omat",
    }
    assert settings == {"matmul_precision": "highest"}
    assert set(spec.scientific_payload()) == {"kind"} | set(variant) | set(settings)


def test_scientific_payload_holds_the_weights_hash_not_their_path(weights_file):
    weights = LocalWeights(weights_file)
    spec = Weighted(weights=weights)

    payload = json.dumps(spec.scientific_payload(mode="json"))

    assert weights.sha256 in payload
    assert str(weights_file) not in payload
    assert "environment_profile" not in spec.scientific_payload()


def test_same_weights_at_two_paths_give_the_same_scientific_payload(
    weights_file, tmp_path
):
    copy = tmp_path / "elsewhere" / "copy.model"
    copy.parent.mkdir()
    copy.write_bytes(weights_file.read_bytes())

    first = Weighted(weights=LocalWeights(weights_file))
    second = Weighted(weights=LocalWeights(copy))

    assert first.scientific_payload() == second.scientific_payload()


def test_variant_id_with_local_weights(weights_file):
    weights = LocalWeights(weights_file)
    spec = Weighted(model="large", weights=weights)

    assert spec.variant_name == "large"
    assert spec.variant_id == f"weighted/large+local:{weights.sha256[:8]}"


def test_generating_variants_does_not_warn():
    import warnings

    class Warns(ModelSpec):
        kind: Literal["warns"] = "warns"
        model: Annotated[Literal["a", "b"], Variant] = "a"

        @model_validator(mode="after")
        def warn_for_b(self):
            if self.model == "b":
                warnings.warn("b is deprecated")
            return self

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert len(Warns.variants()) == 2
