from pathlib import Path

from atomforge_core.resources.resource_models import ExecutionResources
from atomforge_testing import structures
from atomforge_testing import (
    ModelEnvironmentContract,
    ModelEnvironmentResolutionContract,
    ModelManifestCase,
    ModelManifestContract,
    ModelManifestSymbolContract,
    ModelRegistryContract,
    ModelSpecContract,
    ModelSinglePointRuntimeContract,
)

# Replace this import with your plugin's manifest object.
from your_plugin.manifest import your_model_manifest


PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"
RUNTIME_RESOURCES = ExecutionResources(accelerator="cpu", precision="f32")


def your_model_spec_factory(model_cls):
    # Return one representative valid spec for test execution.
    return model_cls(required_option="replace-me")


class TestYourModel(
    ModelManifestContract,
    ModelManifestSymbolContract,
    ModelSpecContract,
    ModelRegistryContract,
    ModelEnvironmentContract,
    ModelEnvironmentResolutionContract,
    ModelSinglePointRuntimeContract,
):
    manifest_case = ModelManifestCase(
        manifest=your_model_manifest,
        entry_point_name="your_model",
        entry_point_package="your-plugin",
        pyproject_path=PYPROJECT,
        expected_entry_point_target="your_plugin.manifest:your_model_manifest",
        model_spec_factory=your_model_spec_factory,
        runtime_structure=structures.small_molecule(),
        runtime_exec_resources=RUNTIME_RESOURCES,
    )
