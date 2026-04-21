import pytest

from atomforge.registry.core.converter import ManifestToRegistrationConverterBase
from atomforge.registry.core.errors import RegistryCoreError


class DummyConverter(ManifestToRegistrationConverterBase):
    error_class = RegistryCoreError

    def _load_components(self, manifest):
        return {
            "environment_factory": self._load_callable(
                manifest.environment_factory, "Environment factory"
            )
        }

    def _build_registration(self, manifest, components, environment_factory):
        return {"wrapped_factory": environment_factory}


class DummyManifest:
    def __init__(self, kind: str, distribution: list[str], environment_factory: str):
        self.kind = kind
        self.distribution = distribution
        self.environment_factory = environment_factory


def test_converter_rejects_mismatched_distribution():
    converter = DummyConverter()
    manifest = DummyManifest(
        kind="dummy",
        distribution=["third-party-plugin"],
        environment_factory="atomforge.task.singlepoint:single_point_environment_factory",
    )

    with pytest.raises(RegistryCoreError):
        converter.convert(
            manifest, entry_point_name="dummy", entry_point_package="atomforge"
        )

def test_converter_wraps_dotted_path_load_failures():
    converter = DummyConverter()

    with pytest.raises(RegistryCoreError):
        converter._load_symbol("atomforge.task.singlepoint:DoesNotExist")
