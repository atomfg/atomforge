# Testing a model plugin

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

For local development, add path sources pointing at your local `atomforge` checkout.
The official plugins are laid out with the plugin two levels below the workspace root
(`<root>/atomforge` next to `<root>/plugins/atomforge-<name>`), which gives:

```toml
[tool.uv.sources]
atomforge_core = { path = "../../atomforge/packages/atomforge-core", editable = true }
atomforge_testing = { path = "../../atomforge/packages/atomforge-testing", editable = true }
```

Adjust the relative paths if your plugin sits somewhere else relative to `atomforge`.

## 2. Add One Test Class Per Model

Copy `tests/test_contracts.py` from the
[model plugin template](https://github.com/atomfg/atomforge/tree/main/templates/model-plugin) into your plugin's `tests/`
directory and fill in:

- the manifest import
- the entry point name
- the package/distribution name
- the entry point target
- a representative `model_spec_factory`

Example:

```python
from pathlib import Path

from atomforge_core.resources.resource_models import ExecutionResources
from atomforge_testing import ModelManifestCase, ModelPluginContract, structures

from my_plugin.manifest import my_model_manifest


PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"
RUNTIME_RESOURCES = ExecutionResources(accelerator="cpu", precision="f32")


def my_model_spec_factory(model_cls):
    return model_cls(required_option="small")


class TestMyModel(ModelPluginContract):
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

`ModelPluginContract` combines all the contracts below. To use only some of
them, inherit from those instead.

## 3. Run the Tests

atomforge-testing installs a pytest plugin, so options, markers and fixtures are
available without any configuration in your `pyproject.toml` or `conftest.py`.

```bash
uv run pytest                            # wiring checks
uv run pytest --atomforge-environment    # + resolve the model environment
uv run pytest --atomforge-runtime        # + execute the model
uv run pytest --atomforge-runtime --atomforge-gpu   # + CUDA GPU combinations
uv run pytest --atomforge-runtime --atomforge-mps   # + Apple MPS combinations
```

The options are the only way to enable the slower checks. The markers
`atomforge_environment`, `atomforge_runtime`, `atomforge_gpu` and
`atomforge_mps` only select:
`uv run pytest --atomforge-runtime -m atomforge_runtime` runs just the runtime
checks.

Your own runtime tests can mark themselves with `@pytest.mark.atomforge_runtime`
and use the session-scoped `atomforge_backend` fixture, one backend shared by
the whole session (see the template's `tests/test_torch_lj.py`). Mark methods
rather than classes that other test classes inherit from: pytest collects class
marks through inheritance.

## What the Contracts Check

- `ModelManifestContract`: manifest type, entry point text, and strict loading.
- `ModelManifestSymbolContract`: one checklist test per manifest symbol.
- `ModelSpecContract`: representative spec construction, and round trips through
  Python and JSON dumps (specs reach the worker as JSON).
- `ModelRegistryContract`: installed package discovery through `ModelRegistry`.
- `ModelEnvironmentContract`: environment factory determinism, provider
  requirements, and dependency summary consistency.
- `ModelEnvironmentResolutionContract`: opt-in provider dry-run resolution for
  the model environment.
- `ModelSinglePointRuntimeContract`: opt-in execution through the backend:
  - `test_declared_property_is_returned[<property>]`: each declared property,
    requested alone, comes back finite and in the right shape: `energy` a
    number, `forces` one 3-vector per atom, `stress` 3×3, `energies` and
    `magmoms` one value per atom. Stress is requested on a periodic structure:
    the case's `runtime_structure` if it is periodic, otherwise
    `structures.periodic_bulk()`.
  - `test_declared_resources_execute_strictly[<accelerator>-<precision>]`: a
    single point runs with `strict=True` for every combination your
    `ResourceCapabilities` declares. A capability left as `None` runs as
    `default`. `gpu` combinations need `--atomforge-gpu`, `mps` combinations
    `--atomforge-mps`.
- `ModelPhysicsContract`: opt-in model-independent physics checks, run on the
  physics structures (below) with the case's `runtime_exec_resources`:
  - `test_energy_is_invariant_under_translation[<structure>]`
  - `test_energy_is_invariant_under_rotation[molecule]`
  - `test_forces_sum_to_zero[molecule]`
  - `test_forces_match_energy_gradient[<structure>]`: central finite
    differences of the energy on the three largest force components, in f64
    if the model declares it. Fails as uninformative if the largest component
    is below ten times the tolerance, since a wrong sign could then pass.
  - `test_repeated_request_gives_same_result[<structure>]`
  - `test_per_atom_energies_sum_to_energy[<structure>]`
  - `test_stress_is_symmetric[slab]`, `[bulk]`

  Deviations are compared with tolerances per precision
  (`atomforge_testing.physics.DEFAULT_TOLERANCES`, measured on the existing
  plugins; `default` precision uses the f32 set). Replace them per precision
  with the case's `tolerances={"f32": Tolerances(...)}`.

  A model that lacks a property a check relies on declares it in the case, and
  the checks that rely on it are skipped:

  ```python
  # Direct forces, rotational symmetry learned from data.
  physics=ModelPhysics(conservative_forces=False, rotation_invariant=False)
  ```

  Zero net force needs conservative and translation-invariant forces;
  symmetric stress needs conservative and rotation-invariant ones.

The environment contracts run once per environment profile: the values of your
spec's `environment_profile` `Literal` (e.g. `[tested]` and `[latest]`), or only
`tested` if the field is not a `Literal`. The contracts are parametrized from the
manifest when pytest collects them; if a manifest symbol cannot be loaded, those
tests are skipped and `ModelManifestSymbolContract` reports the error.

Reference structures are available from `atomforge_testing.structures`:

- `small_molecule()`, `periodic_bulk()`, `isolated_atom()`: small structures
  for the single-point runtime contract.
- `reference_structures()`: the physics structures, near equilibrium with
  every atom slightly displaced (seeded, so always the same):
  `"molecule"` (ethanol), `"slab"` (Cu(111), 2×2, three layers) and `"bulk"`
  (diamond Si). A model that cannot run one of them, or needs others, sets
  `physics_structures={"molecule": ...}` in its case; the checks of a
  structure left out are skipped.

For how the contracts turn this class into tests, and why a test runs, is
skipped or fails, see [How the plugin tests work](plugin-tests.md).

## Common Failures

- `Unknown Model kind`: the plugin entry point is not installed or discoverable.
- `Entry point package ... must be listed`: manifest `distribution` does not
  match the installed package name.
- `returned undeclared requirements`: environment factory returned requirements
  missing from `DependencySummary`.
- Environment resolver failures: the provider cannot solve the generated model
  environment, often due to incompatible Python or dependency constraints.
- Runtime import errors: the model environment requirements are incomplete.
