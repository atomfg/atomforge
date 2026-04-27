import pytest

from atomforge_core.env.factory import EnvironmentFactory
from atomforge_runtime.registry.base_converter import ManifestToRegistrationConverterBase
from atomforge_core.registry.errors import RegistryCoreError
from atomforge_core.registry.symbol_path import SymbolPath


class DummyConverter(ManifestToRegistrationConverterBase):
    error_class = RegistryCoreError

    def _load_components(self, manifest):
        return {
            "environment_factory": self._load_subclass(
                manifest.environment_factory, EnvironmentFactory, "Environment factory"
            )
        }

    def _build_registration(self, manifest, components):
        return {"environment_factory_path": components["environment_factory"]}


class DummyManifest:
    def __init__(
        self, kind: str, distribution: list[str], environment_factory: SymbolPath
    ):
        self.kind = kind
        self.distribution = distribution
        self.environment_factory = environment_factory


def test_converter_rejects_mismatched_distribution():
    converter = DummyConverter()
    manifest = DummyManifest(
        kind="dummy",
        distribution=["third-party-plugin"],
        environment_factory=SymbolPath(
            "atomforge_builtins.task.singlepoint:SinglePointEnvironmentFactory"
        ),
    )

    with pytest.raises(RegistryCoreError):
        converter.convert(
            manifest, entry_point_name="dummy", entry_point_package="atomforge"
        )

def test_converter_wraps_dotted_path_load_failures():
    converter = DummyConverter()

    with pytest.raises(RegistryCoreError):
        converter._load_symbol(
            SymbolPath("atomforge_builtins.task.singlepoint:DoesNotExist")
        )
