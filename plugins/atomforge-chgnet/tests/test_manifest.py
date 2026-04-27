from pathlib import Path
import sys


PLUGIN_SRC = Path(__file__).resolve().parents[1] / "src"

if str(PLUGIN_SRC) not in sys.path:
    sys.path.insert(0, str(PLUGIN_SRC))


def test_chgnet_public_reexport_and_manifest_symbols():
    from atomforge_chgnet import CHGNet
    from atomforge_chgnet.manifest import chgnet_manifest
    from atomforge_chgnet.spec import CHGNet as CHGNetSpec

    assert CHGNet is CHGNetSpec

    assert chgnet_manifest.model_spec.load_symbol() is CHGNetSpec
    assert chgnet_manifest.executor_cls.load_symbol().__name__ == "CHGNetExecutor"
    assert chgnet_manifest.supported_properties.load_symbol()
    assert str(chgnet_manifest.environment_factory_cls) == (
        "atomforge_chgnet.environment:CHGNetEnvironmentFactory"
    )
    assert chgnet_manifest.environment_factory_cls.load_symbol()
    assert chgnet_manifest.metadata.load_symbol().id == "chgnet"
    assert chgnet_manifest.resource_capabilities.load_symbol().accelerator == [
        "cpu",
        "gpu",
        "mps",
    ]
