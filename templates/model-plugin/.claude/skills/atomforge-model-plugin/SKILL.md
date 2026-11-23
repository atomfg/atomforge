---
name: atomforge-model-plugin
description: Implement an atomforge model plugin, which wraps an interatomic potential or other atomistic model (an MLIP such as MACE or Orb, or a classical potential) as a ModelSpec, ModelExecutor and ModelManifest, until the atomforge-testing contracts pass with honest declarations. Use it to create a new plugin from the model plugin template, to add a model to an existing plugin, or to diagnose failing atomforge-testing contracts.
---

# Implementing an atomforge model plugin

A model plugin makes a model usable through atomforge. The host builds a
`ModelSpec`. The model runs in an isolated worker environment, where a
`ModelExecutor` calls the model's own package. A `ModelManifest`, registered
through an entry point, ties the two together.

You do not write the acceptance tests. The `atomforge-testing` contracts are
those tests. You write one test class per model that *declares* what the model
is: its properties, resources, environment profiles and physics. The contracts
then generate tests that check every declaration. The task is done when they
pass and every declaration is true of the model.

Read these when you need detail (published docs, current with the template):

- Models, specs, executors and manifests:
  https://atomfg.github.io/atomforge/concepts/models/
- Testing a model plugin:
  https://atomfg.github.io/atomforge/development/plugin-testing/
- How the plugin tests work (gates, skips, parametrization):
  https://atomfg.github.io/atomforge/development/plugin-tests/
- The template: this repository, if it was started from the template, and
  otherwise https://github.com/atomfg/atomforge-model-plugin-template. Its
  code comments explain each piece.
- The fields of `ModelManifestCase`, `ModelPhysics` and the tolerances: the
  installed source, `atomforge_testing/model_manifest.py` and
  `atomforge_testing/physics.py` in the project's `.venv`.

## Rules

These rules hold throughout. A failing contract always has a cheap wrong fix,
and these rules exclude each one.

1. **Declarations are claims about the model, not test settings.** Change one
   only on evidence from the model itself: its paper, documentation or source.
   Put a comment next to the declaration that cites the evidence. Never change
   one because a test fails.
   - `ModelPhysics(conservative_forces=False)`: only when the model predicts
     forces with a separate output head instead of differentiating the energy.
   - `ModelPhysics(rotation_invariant=False)`: only when rotational symmetry is
     learned from data rather than built into the architecture.
   - `ModelPhysics(translation_invariant=False)`: practically never.
   - `physics_structures`: leave a structure out only when the model cannot
     run it at all (e.g. it has no periodic support), never because its
     result fails a check.
   - Supported properties and resource capabilities: declare everything the
     model really supports. Do not remove one to avoid a failure. A property
     that fails because it is broken is a finding to report.
2. **Never loosen a tolerance** (`tolerances`, `reference_tolerances`) and
   never set `runtime_skip_reason` to get a green run. If you believe a
   default tolerance is wrong for this model, stop and report it with the
   measured deviation.
3. **References are recorded once, then never edited to pass.** A missing
   reference is recorded by the first runtime run. After that, use
   `--force-regen` only after an intended change that you can explain, such
   as a new pinned version.
4. **The host never imports the model's package.** Only the executor module
   imports it, and only inside methods. The model's dependencies go in the
   environment factory, never in `[project] dependencies` or the dev group.
5. **`compute` returns** a `float` energy and float64 numpy arrays that own
   their memory (`np.array(x, dtype=np.float64)`, or
   `t.detach().cpu().numpy().astype(np.float64)` for torch). Units are ASE's:
   eV, Å, eV/Å, and stress in eV/Å³ as a 3×3 array, with ASE's sign
   convention.
6. **The environment factory is deterministic in the spec.** It must not
   inspect the machine. Pin exact versions in `tested`, including torch and
   numpy, and use lower bounds in `latest`. Every requirement and Python
   constraint must also be listed in the `DependencySummary`.
7. **`f32` is strict float32**: float32 storage and computation, without
   reduced-precision matrix multiplication (torch's
   `set_float32_matmul_precision("highest")`). If the library defaults to
   TF32 or similar, switch it off for `f32`. To offer the faster mode, add
   `matmul_precision: Literal["highest", "high"] = "highest"` to the spec,
   and apply `"high"` only on `cuda` with `f32`. Use exactly this name.
8. **Process-wide state is set around every `compute`.** One worker holds
   several model sessions (the same model at two precisions, or two models
   whose environments are identical). If loading the model changes
   process-wide state (torch's default dtype, the float32 matmul precision),
   read it after loading, and set it before and restore it after each
   `compute`, with a context manager. It costs nothing measurable.

## Workflow

### 1. Research the model before writing code

Find the answers in the documentation and paper first, then in the source.
Write them into the plugin's README under "Model notes", with links. They
justify the declarations, and a reviewer checks them there.

- **Package:** the distribution name; the newest version; the Python versions
  it has wheels for; its torch requirement; heavy dependencies that may lack
  wheels (dgl, torch-scatter, h5py, ...).
- **Loading:** the function or class that loads a pretrained model; the
  available checkpoints or variants and their names; where the weights are
  downloaded from and to; whether a download needs an account or a token;
  whether the download is pinned to a revision (see step 2, "Weights").
- **Calling:** the documented inference API. An ASE calculator is acceptable
  and often simplest. A lower-level API gives more control over dtype and
  device.
- **Outputs:** which of energy, forces, stress, per-atom energies and magnetic
  moments it returns. Their units, the stress sign convention, and whether
  stress comes as a 3×3 array or in Voigt order (and which order).
  Stress requested for a structure that is not fully periodic: raise a clear
  error.
- **Forces:** gradients of the energy (conservative), or a direct output head.
  Some models offer both, as a spec option.
- **Symmetry:** rotation invariance or equivariance built into the
  architecture, or learned from data (for example through augmentation).
- **Inputs:** periodic and non-periodic systems; element coverage; whether it
  needs charge or spin (`StructureData` has `charge` and
  `spin_multiplicity`, both optional). atomforge has no rule yet for a model
  that needs them when they are `None`: record what the plugin does in the
  model notes and list it as an open question.
- **Resources:** which accelerators it runs on (CPU, NVIDIA through CUDA, AMD
  through ROCm, Apple MPS), and which precisions on each. Libraries that
  depend on NVIDIA-only packages (warp, cuEquivariance, ...) do not run on
  ROCm. Note any global state that loading changes (torch's default dtype,
  float32 matmul precision, random seeds, thread counts) and whether it is
  restored afterwards.
- **Files outside the environment:** where weights and kernel caches are
  written (for example `~/.cache`). Record them in the model notes; do not
  redirect them.
- **Spec fields:** the choices a user makes (checkpoint, dataset, task head,
  dispersion correction, ...), which of them choose trained parameters and
  which are settings, which combinations are invalid, and which fields have
  no effect for some values of others (Orb's cutoff for OMol models).
- **Local weights:** whether the library loads parameters from a local file
  or directory (a fine-tuned model), in what format, and whether it needs the
  base architecture to load them (a state dict) or not (a whole model).

To try the package, use a scratch environment that is not the plugin's:

```bash
uv run --isolated --no-project --python 3.12 --with "<package>==<version>" python explore.py
```

### 2. Start from the template

For a new plugin, start a repository from the template
(`gh repo create <name> --template atomfg/atomforge-model-plugin-template`, or
a copy of it). Then follow "Make it yours" in its README:

- Rename the distribution (`atomforge-<name>`), the package
  (`atomforge_<name>`) and the model kind. The kind is lowercase with hyphens,
  unique among all plugins, and includes the model's generation where there is
  one (`orb-v3`).
- One model: modules directly in the package. Several models: one subpackage
  per model, each with its own manifest and entry point, and code they share
  at the package root.
- Point the test class in `tests/test_contracts.py` at the new manifest, entry
  point and distribution.
- Delete `tests/test_contracts/torch-lj-*.npz`. Replace
  `tests/test_torch_lj.py` with the model's own tests (step 4).

To add a model to an existing plugin, add its subpackage (moving a flat model
into its own subpackage first), its entry point and a second test class.

**Spec fields and variants.** Every spec field has a role, given with
`Annotated` (see the template's `spec.py`):

- `Variant` for a field that chooses trained parameters (checkpoint, training
  set, task head). Its type must be a `Literal` or `bool` (or their union with
  `None`), so `Spec.variants()` can list every trained model. A free `str` for
  a checkpoint name is not allowed: list the names the tested version knows.
- `Setting` for everything else, even when it changes the numbers (precision
  modes, dispersion).
- `kind` and `environment_profile` take no marker.

Bring every input to a canonical form: where a variant field has no effect
for some values of another, set it to `None` in a `mode="before"` validator,
so each trained model is one variant. Check with
`[v.variant_id for v in Spec.variants()]` that there is one entry per
checkpoint. Order the variant fields so that the generated names read like
the library's names, or override `variant_name`.

Declare `variant_info` in the manifest: a function returning a `VariantInfo`
(training data, level of theory, `checkpoint` with its revision or URL) for
each variant. The spec contract checks that it covers every variant and that
no two share a checkpoint, which catches a missed canonical form.

The contracts run the spec that `model_spec_factory` returns. To run other
variants, name them in the case (`variants=(...)`), or run once with
`--atomforge-all-variants` (say in the model notes how much it downloads).
When variants differ in what the test class declares (for example direct and
conservative forces need different `ModelPhysics`), add a test class per
variant, each naming its variants; references are named
`<kind>-<variant>-<structure>`, so the classes can share a module. When a
declared property is missing for some variants (a checkpoint without a stress
head), keep the declaration, raise a clear error for those variants, and
record it in the model notes.

**Local weights.** If the library loads parameters from a local file (step
1), declare `weights: LocalWeights | None = None` in the spec and pass
`spec.weights.path` to the library in the executor; atomforge has checked the
hash before the executor is made. With a state-dict format, the variant
fields select the architecture to load into. Give the case a
`local_weights_factory(spec, directory) -> LocalWeights` that writes the
variant's own parameters (download its checkpoint, using the URL in
`variant_info`, into a cache, and copy it under `directory`); the local
weights contract checks that they give the variant's results. If the library
cannot load local parameters, leave the field out.

**Weights.** Pin the weights where the library allows it: if it accepts a
file path, or a revision or URL, download the checkpoint yourself (for
example with `huggingface_hub.hf_hub_download`) at a fixed commit for the
`tested` profile and at the newest for `latest`, and pass the result to the
library. A re-upload under the same name then changes only `latest`, where
the reference contract catches it. Keep the mapping (file names, revisions)
in a host-side module, so it can be tested without the model's packages.
Where the library allows no pinning, say in the model notes that the weights
are unpinned.

### 3. Implement in gate order

Each gate is slower than the one before it. Get one green before moving on.
Write every run's full output to a file, and read the file afterwards, so
that a failure is never lost:

```bash
uv run pytest -rfEs > wiring.log 2>&1                          # seconds
uv run pytest --atomforge-environment -rfEs > env.log 2>&1     # resolves the worker env
uv run pytest --atomforge-runtime -rfEs -k "<group>" > run.log 2>&1   # see the table below
```

1. **Wiring:** spec, definitions, environment, manifest, `pyproject.toml`
   entry point, test class. Run `uv run pytest`.
2. **Environment:** `--atomforge-environment`. Fix version and Python
   constraints here. A cap (`<3.14`, say) needs a comment that names the
   dependency that forces it. The template's CI resolves with the CPU-only
   torch index first, which mirrors some packages (numpy, markupsafe) only up
   to some version. Check the pins as CI will:
   `UV_INDEX=https://download.pytorch.org/whl/cpu uv run pytest --atomforge-environment`.
   Resolution uses the newest Python the profile's constraint allows, so a
   `latest` profile without an upper bound meets each new CPython first,
   often before its dependencies have wheels for it.
3. **Executor:** `--atomforge-runtime`, one group of contracts at a time:

   | Group | `-k` expression |
   |---|---|
   | single point | `"declared_property or declared_resources"` |
   | result types | `"is_a_float or float64 or finite or described or later_compute"` |
   | physics | `"invariant or gradient or repeated or sum_to or symmetric"` |
   | references | `matches_reference` |
   | local weights | `local_weights` |

   The first runtime run builds the environment and downloads the weights,
   which can take many minutes. Run it in the background and read the log
   when it finishes.
4. **References:** the first full runtime run records
   `tests/test_contracts/<kind>-<variant>-<structure>.npz` and fails on purpose. Check
   that the recorded values are plausible (an energy per atom of a few eV
   with a negative sign for a molecule, forces of order 0.01 to 1 eV/Å), then
   run again.
5. **Accelerators:** declare the precisions per accelerator, for example
   `precision={"cpu": ["f32", "f64"], "cuda": ["f32", "f64"], "mps": ["f32"]}`
   (torch has no float64 on MPS). The contracts test exactly the declared
   pairs. Add `--atomforge-cuda` on an NVIDIA machine, `--atomforge-rocm` on
   an AMD one and `--atomforge-mps` on Apple silicon.
   - `cuda` may be declared before the model has run on an NVIDIA GPU, when
     the library supports CUDA and the device code is plain torch. Say in the
     model notes and the report that it has not run there.
   - `rocm` only after the model has run on an AMD GPU: libraries often
     depend on NVIDIA-only packages. ROCm builds of torch still call the
     device `"cuda"`, so the translation maps `rocm` to `"cuda"`.
   - With precision declared, the resolved precision is never `None`; a
     `None` mapping only matters for models that do not use the knob.

When a test fails, read [references/diagnosis.md](references/diagnosis.md)
before you change anything.

### 4. Check the numbers independently

The reference contract only detects drift from the plugin's own first
recording. A wrong unit, stress sign or Voigt order, or an energy missing a
constant, gets recorded as the reference and then passes. (A real case: an
Orb plugin called the model's forward pass, which leaves out the per-element
reference energies that the library's `predict()` and ASE calculator add.
Forces were right, absolute energies were off by several eV per atom, and
every contract passed.) So add a test, marked
`@pytest.mark.atomforge_runtime`, that compares atomforge's single point with
values that the model's own package computes outside atomforge:

- Write a small script, `tests/<model>_values.py`, that builds fixed
  structures with ASE, runs the model through its own documented calculator
  or API (step 1's scratch environment, with the `tested` pins), and writes
  energy, forces and stress, the structures and the package versions to
  `tests/<model>_values.json`. Write the file from the script rather than
  printing: libraries print banners to stdout. Include at least one periodic
  structure if stress is declared.
- The test reads the JSON file. Compare the **absolute** energy, not only
  differences, and cover each variant the spec offers. If that downloads a
  lot, say how much in the README. The contracts run only the case's variants
  unless `--atomforge-all-variants` is given, so check the physics claims of
  the others (a rotation, say) outside atomforge too, and record the result in
  the model notes.
- Compare at f64 if declared, otherwise at f32, with tolerances that reflect
  that precision.

The template's `test_torch_lj.py` shows the pattern, with an analytic
potential in place of the package.

### 5. Finish and report

The work is done when:

- `uv run pytest --atomforge-environment --atomforge-runtime -rfEs` passes,
  with GPU and MPS too where the machine has them;
- every skip in that run has a reason that is true (list them with `-rs`);
- the README's "Model notes" justify each declaration.

Report:

- the declarations (properties, resources, profiles, `ModelPhysics`,
  physics structures) and the evidence for each;
- every skipped test and its reason;
- deviations, limitations and anything that did not work;
- open questions for the maintainer.
