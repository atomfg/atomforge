# Diagnosing failing contracts

Read the whole failure first: the message names the structure, the deviation
and the tolerance. Then find the test below. Each entry gives the likely
causes, most common first, and the fix. "Not a fix" lists the changes that
make the test pass without making the plugin right. The rules in SKILL.md
forbid them.

To look at what `compute` returns, without the pydantic conversion of a
single point, use the `describe_model_result` task:

```python
from atomforge_builtins.task.describe_model_result import DescribeModelResult

description = backend.execute(
    DescribeModelResult(structure=structure, properties={"energy", "forces"}),
    model=spec,
)
print(description.fields)
```

## Wiring (plain `uv run pytest`)

| Symptom | Cause | Fix |
|---|---|---|
| Collection error `ModuleNotFoundError` for the model's package | A host-side module imports it, or the executor imports it at module level | Move the import into the executor's methods |
| Tests skipped with id `[unloadable]` | A `module:attr` string in the manifest is wrong; the symbol contract's failure gives the error | Fix the string |
| `Unknown Model kind` | The entry point is not installed. The package was not synced after `pyproject.toml` changed | `uv sync`, check `[project.entry-points.'atomforge.model']` |
| `Entry point package ... must be listed` | The manifest's `distribution` does not match the package | Use the import name, as in the template (`["atomforge_<name>"]`) |
| `returned undeclared requirements` | The environment factory returns a requirement or Python constraint missing from `DependencySummary` | Add it to the summary |
| Spec round trip fails | A spec field that does not serialise to JSON (a path, a callable, a numpy value) | Use a JSON type; specs reach the worker as JSON |
| `defaults to tested` fails | `environment_profile` does not default to `"tested"` | Make `"tested"` the default |

## Environment (`--atomforge-environment`)

| Symptom | Cause | Fix |
|---|---|---|
| No solution, a dependency has no wheel for the chosen Python | `latest` allows a Python the dependency has no wheels for yet | Cap Python with a comment that names the dependency, and when to lift the cap |
| No solution with a custom index set (for example the CPU torch index on CI) | That index mirrors a package (numpy, markupsafe) only up to some version, and uv does not fall back to PyPI | Pin to a version the index has |
| Conflict between the model's package and the pinned torch | The model package caps torch | Pin the torch version its release was tested with |

## Single point (`declared_property`, `declared_resources`)

| Symptom | Cause | Fix |
|---|---|---|
| Worker init timeout | Weights still downloading | Raise `ATOMFORGE_WORKER_INIT_TIMEOUT_S`, or download them once beforehand |
| `... was declared but not returned` | `compute` ignores a requested property, or reads the wrong output key | Return every requested, declared property |
| Wrong shape for stress | Voigt (6,) returned instead of 3×3 | Convert, in the order the library documents |
| A strict `cpu-f64` (or `cuda-...`, `mps-...`) run fails | The executor ignores `resolved_resources`, or the library cannot do that pair | Translate the resources (see the template's `resources.py`). If the library really cannot, remove that precision for that accelerator only (the mapping is per accelerator) and record why in the model notes |

## Result types

| Symptom | Cause | Fix |
|---|---|---|
| `dtype: float32` | The model ran in f32 and returned its array | `.astype(np.float64)` |
| Energy is `np.float32` or a 0-d array/tensor | No conversion | `float(...)` |
| `test_result_is_not_changed_by_a_later_compute` fails | The array is a view of a tensor or buffer the model reuses (`.numpy()` on a CPU tensor is a view) | Copy: `np.array(x, dtype=np.float64)` or `.astype(np.float64)` |

## Physics

| Symptom | Cause | Fix |
|---|---|---|
| Translation changes the energy | The structure conversion drops or mangles `cell` or `pbc`, or wraps atoms inconsistently | Fix the conversion. Compare with the library on the same ASE `Atoms` |
| Rotation changes the energy by much more than the tolerance | A conversion bug, as above | Fix the conversion |
| Rotation changes the energy slightly, and the architecture is not equivariant by construction | Symmetry learned from data | `ModelPhysics(rotation_invariant=False)` with the paper's statement cited. Only with that evidence |
| Forces do not match the energy gradient by a large factor or with the wrong sign | Unit conversion, a missing minus sign, forces from a different output than the energy | Fix it. Check against the package directly (SKILL.md step 4) |
| Gradient mismatch, and the model has a direct force head | Direct forces are not gradients | `ModelPhysics(conservative_forces=False)` with the evidence cited, or use the conservative mode if the spec offers one |
| Gradient check `uninformative` | The forces on that structure are too small to tell right from wrong | Do not loosen anything. Report it: the contract's structure may need larger forces for this model |
| Repeated request differs | Dropout or other training-mode behaviour (`model.eval()` not called), nondeterministic kernels, or state carried between calls | `eval()`, `torch.no_grad()` where forces do not need autograd, reset per-call state |
| Results differ after another precision or session loaded in the same worker | The library changes process-wide state (for example `torch.set_default_dtype` or `torch.set_float32_matmul_precision`) on load | Save the state after loading, and set and restore it around every `compute` (a context manager) |
| Net force not zero | Not translation invariant or not conservative, or a conversion bug | As for translation and gradient |
| Stress not symmetric | Wrong Voigt order, or a non-conservative stress head | Check the order against the library's docs |
| Per-atom energies do not sum to the energy | Per-atom energies exclude a reference or dispersion term that the total includes | Declare `energies` only if they sum to the total. Otherwise drop the declaration and note why |

Not a fix: `ModelPhysics(...=False)` without evidence from the model,
leaving out a structure, changing `tolerances`.

## References

| Symptom | Cause | Fix |
|---|---|---|
| `File not found in data directory, created: ...npz` | First run, a reference was recorded | Check that the values are plausible, commit, run again |
| `no reference ...; run test_matches_reference[tested-...]` | `latest` ran before `tested` recorded | Run the `tested` reference test first |
| `latest` differs from the reference | A newer version of the package changes the numbers | Report it. This is what the check is for. Do not regenerate unless the `tested` pins change |
| `tested` differs from the reference on a rerun | Nondeterminism (see "Repeated request differs"), or the run used other resources than the recording | Fix the nondeterminism |

Not a fix: `--force-regen` to make a failure go away, changing
`reference_tolerances`.
