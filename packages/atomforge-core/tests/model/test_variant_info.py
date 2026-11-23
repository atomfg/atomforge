"""Acceptance tests for the declared facts about a variant ("Variants,
settings and local weights in the spec, design" in the engineering log)."""

from atomforge_core.model.metadata import VariantInfo
from atomforge_core.registry.model_manifest import ModelManifest


def test_every_variant_info_field_is_optional():
    info = VariantInfo()

    assert info.description is None
    assert info.training_data == ()
    assert info.level_of_theory is None
    assert info.checkpoint is None
    assert info.parameters is None


def test_variant_info_holds_the_facts():
    info = VariantInfo(
        description="Conservative forces, infinite cutoff",
        training_data=("OMat24",),
        level_of_theory="PBE",
        checkpoint="orb-v3-conservative-inf-omat",
        parameters=25_000_000,
    )

    assert info.training_data == ("OMat24",)


def _manifest(**extra):
    return ModelManifest(
        kind="fake-model",
        model_spec="pkg.mod:Spec",
        executor_cls="pkg.mod:Executor",
        supported_properties="pkg.mod:Properties",
        environment_factory_cls="pkg.mod:Factory",
        metadata="pkg.mod:Metadata",
        resource_capabilities="pkg.mod:Capabilities",
        **extra,
    )


def test_variant_info_is_optional_in_the_manifest():
    assert _manifest().variant_info is None


def test_the_manifest_takes_a_variant_info_symbol_path():
    manifest = _manifest(variant_info="pkg.mod:variant_info")

    assert str(manifest.variant_info) == "pkg.mod:variant_info"
