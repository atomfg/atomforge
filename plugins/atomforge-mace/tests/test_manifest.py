from pathlib import Path
import sys


PLUGIN_SRC = Path(__file__).resolve().parents[1] / "src"

if str(PLUGIN_SRC) not in sys.path:
    sys.path.insert(0, str(PLUGIN_SRC))


def test_mace_public_reexport_and_manifest_symbols():
    from atomforge_mace import MACE
    from atomforge_mace.manifest import mace_manifest
    from atomforge_mace.spec import MACE as MACESpec

    assert MACE is MACESpec
    assert mace_manifest.model_spec.load_symbol() is MACESpec
    assert mace_manifest.executor_cls.load_symbol().__name__ == "MACEExecutor"
    assert mace_manifest.supported_properties.load_symbol()
    assert str(mace_manifest.environment_factory_cls) == (
        "atomforge_mace.environment:MACEEnvironmentFactory"
    )
    assert mace_manifest.environment_factory_cls.load_symbol()
    assert mace_manifest.metadata.load_symbol().id == "mace"
    assert mace_manifest.resource_capabilities.load_symbol().precision == [
        "f32",
        "f64",
    ]
