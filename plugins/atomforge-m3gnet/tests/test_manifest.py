from pathlib import Path
import sys


PLUGIN_SRC = Path(__file__).resolve().parents[1] / "src"

if str(PLUGIN_SRC) not in sys.path:
    sys.path.insert(0, str(PLUGIN_SRC))


def test_m3gnet_public_reexport_and_manifest_symbols():
    from atomforge_m3gnet import M3GNet
    from atomforge_m3gnet.manifest import m3gnet_manifest
    from atomforge_m3gnet.spec import M3GNet as M3GNetSpec

    assert M3GNet is M3GNetSpec
    assert m3gnet_manifest.model_spec.load_symbol() is M3GNetSpec
    assert m3gnet_manifest.executor_cls.load_symbol().__name__ == "M3GNetExecutor"
    assert m3gnet_manifest.supported_properties.load_symbol()
    assert str(m3gnet_manifest.environment_factory_cls) == (
        "atomforge_m3gnet.environment:M3GNetEnvironmentFactory"
    )
    assert m3gnet_manifest.environment_factory_cls.load_symbol()
    assert m3gnet_manifest.metadata.load_symbol().id == "m3gnet"
    assert m3gnet_manifest.resource_capabilities.load_symbol().accelerator == ["cpu"]


def test_m3gnet_entry_point_target():
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    contents = pyproject.read_text()

    assert 'm3gnet = "atomforge_m3gnet.manifest:m3gnet_manifest"' in contents
