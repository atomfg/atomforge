# Testing a Model Plugin

Use `atomforge-testing` to check that a model plugin is wired the way AtomForge
expects.

## 1. Add the Test Dependency

```toml
[dependency-groups]
dev = [
    "atomforge-testing[runtime]",
    "pytest>=9.0.3",
]
```

For local development, add the relevant path source:

```toml
[tool.uv.sources]
atomforge_testing = { path = "../atomforge/packages/atomforge-testing", editable = true }
```

## 2. Add One Test Class Per Model

Copy `templates/test_model_plugin.py` into your plugin's `tests/` directory and
fill in:

- the manifest import
- the entry point name
- the package/distribution name
- the entry point target
- a representative `model_spec_factory`

Example:

```python
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

from my_plugin.manifest import my_model_manifest


PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"
RUNTIME_RESOURCES = ExecutionResources(accelerator="cpu", precision="f32")


def my_model_spec_factory(model_cls):
    return model_cls(required_option="small")


class TestMyModel(
    ModelManifestContract,
    ModelManifestSymbolContract,
    ModelSpecContract,
    ModelRegistryContract,
    ModelEnvironmentContract,
    ModelEnvironmentResolutionContract,
    ModelSinglePointRuntimeContract,
):
    manifest_case = ModelManifestCase(
        manifest=my_model_manifest,
        entry_point_name="my_model",
        entry_point_package="my-plugin",
        pyproject_path=PYPROJECT,
        expected_entry_point_target="my_plugin.manifest:my_model_manifest",
        model_spec_factory=my_model_spec_factory,
        runtime_structure=structures.small_molecule(),
        runtime_exec_resources=RUNTIME_RESOURCES,
    )
```

## 3. Run the Tests

Fast wiring checks:

```bash
uv run pytest
```

Environment resolver checks:

```bash
uv run pytest -m atomforge_environment
```

Runtime execution checks:

```bash
ATOMFORGE_RUN_RUNTIME_TESTS=1 uv run pytest -m atomforge_runtime
```

## What the Contracts Check

- `ModelManifestContract`: manifest type, entry point text, and strict loading.
- `ModelManifestSymbolContract`: one checklist test per manifest symbol.
- `ModelSpecContract`: representative spec construction and Pydantic round-trip.
- `ModelRegistryContract`: installed package discovery through `ModelRegistry`.
- `ModelEnvironmentContract`: environment factory determinism, provider
  requirements, and dependency summary consistency.
- `ModelEnvironmentResolutionContract`: opt-in provider dry-run resolution for
  the model environment.
- `ModelSinglePointRuntimeContract`: declared energy/forces execute through the
  backend-created environment.

Reference structures are available from `atomforge_testing.structures`:

- `small_molecule()`
- `periodic_bulk()`
- `isolated_atom()`

## Common Failures

- `Unknown Model kind`: the plugin entry point is not installed or discoverable.
- `Entry point package ... must be listed`: manifest `distribution` does not
  match the installed package name.
- `returned undeclared requirements`: environment factory returned requirements
  missing from `DependencySummary`.
- Environment resolver failures: the provider cannot solve the generated model
  environment, often due to incompatible Python or dependency constraints.
- Runtime import errors: the model environment requirements are incomplete.
