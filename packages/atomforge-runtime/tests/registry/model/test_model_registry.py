from dataclasses import replace

import pytest

from atomforge_core.registry.symbol_path import SymbolPath
from atomforge_runtime.registry.model.model_registry import ModelRegistry
from atomforge_runtime.registry.strict import RegistryStrictValidationError

from runtime_fakes import build_model_registration


def test_model_registry_registers_runtime_local_registration():
    registry = ModelRegistry()
    registration = build_model_registration()
    registry._register(registration, registration.kind)

    assert registry.get("fake-model").model_spec.__name__ == "FakeModel"


def test_default_can_load_registry_with_invalid_lazy_fields(monkeypatch):
    registration = build_model_registration()

    def fake_load_entry_points(self):
        self._register(registration, registration.kind)
        broken = replace(
            registration,
            kind="broken-fake-model",
            metadata_path=SymbolPath("runtime_fakes:FakeTask"),
        )
        self._register(broken, broken.kind)

    monkeypatch.setattr(ModelRegistry, "_load_entry_points", fake_load_entry_points)

    registry = ModelRegistry.default()

    assert registry.get("broken-fake-model").kind == "broken-fake-model"


def test_strict_aggregates_lazy_field_failures(monkeypatch):
    registration = build_model_registration()

    def fake_load_entry_points(self):
        self._register(registration, registration.kind)
        broken_one = replace(
            registration,
            kind="broken-one",
            metadata_path=SymbolPath("runtime_fakes:FakeTask"),
            resource_capabilities_path=SymbolPath("runtime_fakes:FakeMetadata"),
        )
        broken_two = replace(
            registration,
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

