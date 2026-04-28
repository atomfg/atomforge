from dataclasses import replace

import pytest

from atomforge_core.registry.symbol_path import SymbolPath
from atomforge_runtime.registry.model.model_registry import ModelRegistry
from atomforge_runtime.registry.strict import RegistryStrictValidationError


def test_default_model_registry_loads_builtin_models():
    registry = ModelRegistry.default()
    assert registry.get("ase-lj").model_spec.__name__ == "LennardJones"


def test_strict_model_registry_loads_builtin_models():
    registry = ModelRegistry.strict()
    assert registry.get("ase-lj").model_spec.__name__ == "LennardJones"


def test_default_can_load_registry_with_invalid_lazy_fields(monkeypatch):
    original_load_entry_points = ModelRegistry._load_entry_points

    def fake_load_entry_points(self):
        original_load_entry_points(self)
        broken = replace(
            self.get("ase-lj"),
            kind="broken-ase-lj",
            metadata_path=SymbolPath("runtime_fakes:FakeTask"),
        )
        self._register(broken, broken.kind)

    monkeypatch.setattr(ModelRegistry, "_load_entry_points", fake_load_entry_points)

    registry = ModelRegistry.default()

    assert registry.get("broken-ase-lj").kind == "broken-ase-lj"


def test_strict_aggregates_lazy_field_failures(monkeypatch):
    original_load_entry_points = ModelRegistry._load_entry_points

    def fake_load_entry_points(self):
        original_load_entry_points(self)
        broken_one = replace(
            self.get("ase-lj"),
            kind="broken-one",
            metadata_path=SymbolPath("runtime_fakes:FakeTask"),
            resource_capabilities_path=SymbolPath("runtime_fakes:FakeMetadata"),
        )
        broken_two = replace(
            self.get("ase-lj"),
            kind="broken-two",
            supported_properties_path=SymbolPath("runtime_fakes:FakeMetadata"),
        )
        self._register(broken_one, broken_one.kind)
        self._register(broken_two, broken_two.kind)

    monkeypatch.setattr(ModelRegistry, "_load_entry_points", fake_load_entry_points)

    with pytest.raises(RegistryStrictValidationError) as exc_info:
        ModelRegistry.strict()

    error = exc_info.value
    assert len(error.failures) == 3
    assert {failure.registration_kind for failure in error.failures} == {
        "broken-one",
        "broken-two",
    }
    assert {failure.field_name for failure in error.failures} == {
        "metadata",
        "resource_capabilities",
        "supported_properties",
    }
    assert "runtime_fakes:FakeTask" in str(error)

