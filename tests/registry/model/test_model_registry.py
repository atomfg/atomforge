from atomforge._runtime.registry.model.model_registry import ModelRegistry


def test_default_model_registry_loads_builtin_models():
    registry = ModelRegistry.default()
    assert registry.get("ase-lj").model_spec.__name__ == "LennardJones"
