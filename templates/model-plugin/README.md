# atomforge model plugin template

A complete, working [atomforge](https://github.com/atomfg/atomforge) model plugin:
a Lennard-Jones potential written in PyTorch, with forces from autograd and support
for CPU and CUDA in single and double precision. Copy it and replace the model with
yours.

The comments in the code explain what each piece is for. For the concepts behind
them, see the docs:

- [Models](https://github.com/atomfg/atomforge/blob/main/docs/docs/concepts/models.md):
  specs, executors and manifests
- [Registries](https://github.com/atomfg/atomforge/blob/main/docs/docs/concepts/registries.md):
  how plugins are discovered
- [Testing a model plugin](https://github.com/atomfg/atomforge/blob/main/packages/atomforge-testing/docs/model-plugin-testing.md)

## Layout

```
src/atomforge_template/
├── spec.py          # user-facing settings (host)
├── definitions.py   # model kind, supported properties, resources, metadata (host)
├── environment.py   # the worker environment: the model's real dependencies (host)
├── resources.py     # atomforge resource names -> torch device and dtype
├── executor.py      # runs the model; the only module that imports torch (worker)
└── manifest.py      # ties the above together; target of the entry point
```

The host never installs torch. If a host-side module imports it, the tests fail.

A plugin can provide several models. Then give each model its own subpackage with
these modules, a manifest and an entry point per model, and put code they share at
the package root.

## Run the tests

```bash
uv run pytest                            # wiring
uv run pytest --atomforge-environment    # + the model environment resolves
uv run pytest --atomforge-runtime        # + runs the model
```

The options combine. Add `--atomforge-gpu` on a machine with a CUDA GPU, and
`--atomforge-mps` on a Mac with Apple silicon if your model declares `mps`. Use `-m`
to select, e.g. `uv run pytest --atomforge-runtime -m atomforge_runtime` runs only
the tests that execute the model.

## Make it yours

1. Rename the distribution (`pyproject.toml`), the package `atomforge_template` and
   the model kind `torch-lj`. Update the entry point and the strings in
   `manifest.py` to match.
2. `[tool.uv.sources]` in `pyproject.toml` says where atomforge comes from. Keep
   it, point it at a newer atomforge commit, or at your own atomforge checkout.
3. Replace the spec fields, the requirements in `environment.py` and the model in
   `executor.py`. Update the supported properties, resource capabilities and
   metadata in `definitions.py`.
4. Rewrite `resources.py` for your framework, and replace the reference values in
   `tests/test_torch_lj.py` with ones for your model.
