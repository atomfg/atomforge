"""Acceptance tests for "Variants, settings and local weights in the spec,
design" in the engineering log: model provenance names the variant and the
local weights' hash."""

from atomforge.backend.subprocess._provenance import build_model_provenance
from atomforge_core.model.weights import LocalWeights
from atomforge_core.provenance import payload_hash

from variant_specs import OrbLike, WeightedLike, registry


def test_provenance_carries_the_variant_id():
    provenance = build_model_provenance(OrbLike(), registry())

    assert provenance.variant_id == "orb-like/conservative-inf-omat"
    assert provenance.weights_sha256 is None


def test_provenance_carries_the_local_weights_hash(tmp_path):
    path = tmp_path / "fine-tuned.model"
    path.write_bytes(b"fine-tuned parameters")
    weights = LocalWeights(path)
    spec = WeightedLike(model="large", weights=weights)

    provenance = build_model_provenance(spec, registry())

    assert provenance.weights_sha256 == weights.sha256
    assert provenance.variant_id == f"weighted-like/large+local:{weights.sha256[:8]}"


def test_payload_hash_uses_the_scientific_payload(tmp_path):
    first = tmp_path / "a" / "fine-tuned.model"
    second = tmp_path / "b" / "fine-tuned.model"
    for path in (first, second):
        path.parent.mkdir()
        path.write_bytes(b"fine-tuned parameters")

    one = build_model_provenance(WeightedLike(weights=LocalWeights(first)), registry())
    two = build_model_provenance(WeightedLike(weights=LocalWeights(second)), registry())

    assert one.payload_hash == two.payload_hash
    spec = WeightedLike(weights=LocalWeights(first))
    assert one.payload_hash == payload_hash(spec.scientific_payload())
