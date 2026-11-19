# How the plugin tests work

A model plugin gets its tests from `atomforge-testing`. The plugin writes one
short class per model, and pytest turns it into a few dozen tests that check the
plugin is wired the way atomforge expects, that its environment resolves, that
the model runs, and that its results obey basic physics.

This page explains how that happens: what the class gives you, where each test
comes from, and why a test runs, is skipped or fails. For the steps to set up the
tests in a new plugin, see the reference in
`packages/atomforge-testing/docs/model-plugin-testing.md`.

## The class you write

This is the test class of the model plugin template (`templates/model-plugin`):

```python
class TestTorchLJ(ModelPluginContract):  # (1)!
    manifest_case = ModelManifestCase(  # (2)!
        manifest=torch_lj_manifest,  # (3)!
        entry_point_name="torch_lj",  # (4)!
        entry_point_package="atomforge-template",
        pyproject_path=PYPROJECT,
        expected_entry_point_target="atomforge_template.manifest:torch_lj_manifest",
        model_spec_factory=torch_lj_spec_factory,  # (5)!
        runtime_structure=structures.small_molecule(),  # (6)!
        runtime_exec_resources=ExecutionResources(accelerator="cpu", precision="f32"),  # (7)!
        physics_structures={"molecule": structures.ethanol()},  # (8)!
    )
```

1.  `ModelPluginContract` contains no tests of its own. It inherits from eight
    *contracts*, classes of test methods that know nothing about any particular
    model. Pytest collects inherited `test_*` methods, so `TestTorchLJ` gets all
    of them.
2.  The *case*: everything the contracts need to know about this model. Each
    test method reads it as `self.case`. It is a dataclass, so a misspelt field
    name fails when pytest imports the test module.
3.  The model's `ModelManifest`. Most tests are driven by what it declares: its
    supported properties, resource capabilities and environment profiles decide
    which tests exist (see [Parametrization](#tests-made-from-your-declarations)).
4.  The entry point the plugin registers in its `pyproject.toml`, the
    distribution that provides it and the `module:attr` it must point at. The
    manifest and registry contracts check that these agree with each other and
    with the installed package.
5.  A function that receives the model's spec class and returns one valid,
    representative spec. Every test that needs a spec, including every model
    run, uses this one. The default calls the class with no arguments.
6.  The structure for the basic runtime tests (`small_molecule()` by default).
    A test of stress uses `structures.periodic_bulk()` instead when this
    structure is not periodic.
7.  The resources for the runtime and physics tests (CPU and f32 by default).
8.  The structures for the physics checks. By default they are all three
    reference structures, a molecule, a slab and a bulk crystal; this model only
    handles non-periodic systems, so it keeps the molecule, and the checks on the
    slab and bulk are skipped.

Three fields are not used here: `runtime_skip_reason` skips every test that
runs the model, with that reason; `physics` declares physical properties the
model does not have (see [Skips](#why-a-test-is-skipped)); `tolerances` replaces
the physics checks' default tolerances for a precision.

## What it gives

For the template, the class collects 58 tests. They come from the eight
contracts:

| Contract | Tests for the template | What it checks | Needs |
|---|---|---|---|
| `ModelManifestContract` | 4 | the manifest is a `ModelManifest`; the `pyproject.toml` entry point targets it; it converts to a registration and every path in it loads | |
| `ModelManifestSymbolContract` | 8 | each symbol the manifest names loads and has the right type (spec, executor, properties, environment factory, metadata, resource capabilities, optional probe and task overrides) | |
| `ModelSpecContract` | 6 | the factory's spec has the manifest's `kind`, survives a round trip through Python and JSON (specs reach the worker as JSON), defaults to the `tested` profile and rejects an unknown one | |
| `ModelRegistryContract` | 4 | the installed package is found by `ModelRegistry.default()`, with the same kind, source and spec class | |
| `ModelEnvironmentContract` | 6 × 2 profiles | the environment factory builds an `EnvironmentSpec`, the same one twice, and only from requirements, Python and channels its `DependencySummary` declares | |
| `ModelEnvironmentResolutionContract` | 1 × 2 profiles | the environment provider (uv) resolves that environment | `--atomforge-environment` |
| `ModelSinglePointRuntimeContract` | 2 properties + 4 resource combinations | each declared property comes back finite and in the right shape; each declared accelerator and precision runs with `strict=True` | `--atomforge-runtime` (GPU: also `--atomforge-gpu`) |
| `ModelPhysicsContract` | 16 | rigid-motion invariance, zero net force, forces against the energy gradient, repeatability, per-atom energies and symmetric stress | `--atomforge-runtime` |

The first five contracts only import the plugin; they run in a second, with a
plain `uv run pytest`. The last three create the model's environment or run the
model, and are switched on by command-line options (see [Gates](#gates)).

## How a class becomes tests

Pytest builds the tests in three steps before it runs any of them, and the test
itself can still decide to skip:

```mermaid
flowchart LR
    A["collect<br/>inherited test methods"] --> B["parametrize<br/>from the manifest"]
    B --> C["gate<br/>by command-line option"]
    C --> D["run<br/>skip if the case or model<br/>does not apply"]
    D --> E["assert"]
```

All of it is done by the pytest plugin that `atomforge-testing` installs
(`atomforge_testing/plugin.py`, registered through the `pytest11` entry point).
Installing the package is enough: there is nothing to add to `conftest.py` or
the pytest configuration.

### Tests made from your declarations

Some test methods take an argument named after a declaration. When pytest
collects such a method on a class with a `manifest_case`, the plugin's
`pytest_generate_tests` hook loads the declaration from the manifest and makes
one test per value:

| Argument | Values from the manifest | For the template |
|---|---|---|
| `atomforge_declared_property` | the supported properties | `[energy]`, `[forces]` |
| `atomforge_declared_resources` | every accelerator × precision in the resource capabilities; a knob set to `None` gives `default` | `[cpu-f32]`, `[cpu-f64]`, `[gpu-f32]`, `[gpu-f64]` |
| `atomforge_environment_profile` | the values of the spec's `environment_profile` `Literal`, or only `tested` | `[tested]`, `[latest]` |

The values in brackets become part of the test id, so
`test_declared_property_is_returned[forces]` is the test that requests forces
alone. Declaring a new property or precision therefore adds tests by itself,
and a plugin cannot leave a declaration untested.

The declarations are loaded at collection time. If one cannot be loaded (a
wrong `module:attr` path, an import error), its tests become a single skipped
test with id `[unloadable]` and the error as the reason, and the symbol contract
reports the error as a failure.

The physics checks are parametrized differently: by structure name, fixed in
the contract rather than read from the manifest. Each check lists the reference
structures it applies to: translation, the gradient, repeatability and per-atom
energies on all three (`[molecule]`, `[slab]`, `[bulk]`), rotation and net force
on the molecule only (the rotation turns the atoms but not the cell, so it is
only rigid without periodic boundaries), and stress symmetry on the two
periodic structures.

### Gates

Creating an environment or running a model takes from seconds to many minutes,
so those tests are off unless asked for. Each such test method carries a
marker, and the plugin skips every marked test whose option is not given:

| Marker | Option | Used by |
|---|---|---|
| `atomforge_environment` | `--atomforge-environment` | environment resolution |
| `atomforge_runtime` | `--atomforge-runtime` | the single-point and physics contracts |
| `atomforge_gpu` | `--atomforge-gpu` | resource combinations on `gpu` |
| `atomforge_mps` | `--atomforge-mps` | resource combinations on `mps` |

The GPU and MPS markers are added to individual parameters, so
`[cpu-f32]` runs on any machine while `[gpu-f32]` waits for both
`--atomforge-runtime` and `--atomforge-gpu`. The options are the only switch:
a marker given to `-m` selects tests but does not enable them.

```bash
uv run pytest                                          # wiring only
uv run pytest --atomforge-environment --atomforge-runtime   # everything this machine can run
uv run pytest --atomforge-runtime -k "gradient and bulk"    # one check on one structure
```

### Why a test is skipped

A test that passed the gate can still skip itself when it starts, because the
check does not apply. The reason is in the skip message (`pytest -rs` lists
them). Running the template with both options gives 44 passed and 14 skipped:

| Skip reason | Tests | Why |
|---|---|---|
| `pass --atomforge-gpu to run` | 2 | gated (the GPU combinations) |
| `torch-lj does not declare energies` | 3 | the per-atom energy check needs a property the model does not declare |
| `torch-lj does not declare stress` | 2 | likewise for stress symmetry |
| `the case has no slab physics structure` | 3 | `physics_structures` left the slab out |
| `the case has no bulk physics structure` | 3 | likewise for bulk |
| `manifest does not declare task override executors` | 1 | nothing to check |

A physics check can also skip because the case declares that the model lacks a
physical property the check relies on. These are declared with `ModelPhysics`,
in which every property is claimed by default:

```python
physics=ModelPhysics(conservative_forces=False, rotation_invariant=False)
```

| Declared absent | Checks skipped |
|---|---|
| `conservative_forces` | forces against the energy gradient, zero net force, symmetric stress |
| `translation_invariant` | translation invariance, zero net force |
| `rotation_invariant` | rotation invariance, symmetric stress |

The skip then reads `the case declares ModelPhysics(rotation_invariant=False)`.
A check is skipped for one reason only, tried in this order: the declared
physics, the declared properties, then the physics structures.

A skip is the contracts saying "this does not apply", not "this is broken":
nothing that fails is turned into a skip. A declaration that is wrong the other
way, a property claimed that the model does not have, shows up as a failure.

## How a test runs the model

The runtime and physics tests run the model the way a user would. Each run
builds a `SinglePoint` task for the structure and the requested properties,
takes the spec from `model_spec_factory`, and calls
`backend.execute(task, model=spec, exec_resources=resources)`.

The backend comes from the `atomforge_backend` fixture: one `SubprocessBackend`
for the whole pytest session, shut down at the end. The first run creates the
model's environment and starts a worker, which can take minutes; the following
runs reuse both. Your own runtime tests can use the same fixture (mark them
`@pytest.mark.atomforge_runtime`), and a `conftest.py` can override it to run
the contracts on another backend.

The resources are the case's `runtime_exec_resources`, except in two places:
`test_declared_resources_execute_strictly` uses each declared combination with
`strict=True`, so the run fails instead of falling back to another accelerator
or precision; and the gradient check uses f64 when the model declares it, so
the finite difference is not drowned in rounding.

## How the physics checks decide

A physics check compares a deviation with a tolerance, for example the change
in energy per atom after a rigid translation. The deviation functions are in
`atomforge_testing.physics`, and the tolerances depend on the precision the
model ran at: `DEFAULT_TOLERANCES` holds an `f32` and an `f64` set, and a model
that does not use the precision knob (`default`) gets the looser `f32` set. The
values were measured on the existing plugins; the method and data are in the
workspace research post "Default tolerances for the atomforge-testing physics
checks". A case replaces a set with
`tolerances={"f32": Tolerances(...)}`.

The gradient check needs one more decision. It displaces an atom by a small
step in each direction, and compares the force with minus the change in energy
over the step, for the three largest force components. If the forces are tiny,
a force with the wrong sign would also pass, so the check fails as
*uninformative* when the largest component is below ten times its tolerance.
The fix is a physics structure with larger forces, not a looser tolerance.

The failure messages give the structure, the deviation and the tolerance, so a
failing physics check says how far off the model was:

```text
energy of the molecule changed by 0.000721 eV/atom under a rigid rotation (tolerance 1e-05)
```

## Using only some contracts

`ModelPluginContract` is a convenience. A plugin can inherit from the
contracts it wants instead, for example to leave out the physics checks while
a model is being brought up:

```python
class TestMyModel(
    ModelManifestContract,
    ModelSpecContract,
    ModelSinglePointRuntimeContract,
):
    manifest_case = ModelManifestCase(...)
```

Mark your own test methods rather than a class that others inherit from:
pytest collects class markers through inheritance, so a marker on a base class
would gate every test of every class built on it.
