"""The atomforge-testing contracts: check that the plugin is wired the way atomforge
expects. Add one test class per model in the plugin.

    uv run pytest                            # wiring
    uv run pytest --atomforge-environment    # + the model environment resolves
    uv run pytest --atomforge-runtime        # + runs the model
"""

from pathlib import Path

from atomforge_core.resources.resource_models import ExecutionResources
from atomforge_testing import ModelManifestCase, ModelPluginContract, structures

from atomforge_template.manifest import torch_lj_manifest

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def torch_lj_spec_factory(model_cls):
    # One representative, valid spec for the contracts to use. sigma puts the
    # shortest pair of the ethanol physics structure (the O-H bond) near the
    # minimum, so forces and curvature are of the size real models give.
    return model_cls(epsilon=1.0, sigma=0.8)


class TestTorchLJ(ModelPluginContract):
    manifest_case = ModelManifestCase(
        manifest=torch_lj_manifest,
        entry_point_name="torch_lj",
        entry_point_package="atomforge-template",
        pyproject_path=PYPROJECT,
        expected_entry_point_target="atomforge_template.manifest:torch_lj_manifest",
        model_spec_factory=torch_lj_spec_factory,
        runtime_structure=structures.small_molecule(),
        runtime_exec_resources=ExecutionResources(accelerator="cpu", precision="f32"),
        # The model accepts only non-periodic structures, so the physics
        # checks run on the molecule alone.
        physics_structures={"molecule": structures.ethanol()},
    )
