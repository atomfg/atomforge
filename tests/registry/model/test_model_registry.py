from atomforge.registry.model.registry import ModelRegistry


def test_default_model_registry_loads_builtin_models():
    registry = ModelRegistry.default()

    assert registry.get("ase-lj").model_spec.__name__ == "LennardJones"
    assert registry.get("chgnet").probe is not None
    assert registry.get("mace").probe is not None
