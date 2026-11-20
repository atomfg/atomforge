# Models

In Atomforge, a model is not a Python object that directly performs a calculation in the host process. It is split into two parts:

- A `ModelSpec` that describes which model configuration should be used.
- A `ModelExecutor` that performs model-specific computation inside an isolated worker environment.

This split is central to Atomforge's design. User code can create, serialize, validate, and pass around model specifications without importing the model package itself. Heavy or conflicting dependencies, such as MLIP frameworks and their numerical stacks, are imported only in the worker environment created for that model.

## ModelSpec

A `ModelSpec` is the user-facing description of a model choice. It is a small Pydantic model with strict fields and no calculation methods.

For example, the built-in Lennard-Jones model is configured by a spec like this:

```python
from typing import Literal

from atomforge_core.model.spec import ModelSpec


class LennardJones(ModelSpec):
    kind: Literal["ase-lj"] = "ase-lj"
    sigma: float = 1.0
    epsilon: float = 1.0
    rc: float | None = None
    ro: float | None = None
    smooth: bool = False
```

The `kind` field identifies the model in the [model registry](registries.md). The other fields are model configuration. Creating this object should not require importing ASE, PyTorch, CHGNet, MACE, Orb, or any other model runtime dependency.

## ModelExecutor

A `ModelExecutor` is the worker-side object that knows how to run the model. It receives the `ModelSpec` and resolved execution resources, loads the model dependencies, converts Atomforge's serializable `StructureData` into whatever representation the model library expects, and computes requested properties.

The Lennard-Jones executor illustrates the division of responsibility:

```python
from atomforge_core.model.executor import ModelExecutor
from atomforge_core.model.result import ModelResult
from atomforge_core.property import Property
from atomforge_core.structure import StructureData


class LennardJonesExecutor(ModelExecutor[LennardJones]):
    def __init__(self, spec, resolved_resources):
        super().__init__(spec, resolved_resources)
        from ase.calculators.lj import LennardJones as ASELennardJones

        self._calc = ASELennardJones(
            sigma=spec.sigma,
            epsilon=spec.epsilon,
            rc=spec.rc,
            ro=spec.ro,
            smooth=spec.smooth,
        )

    def compute(
        self, structure: StructureData, properties: frozenset[Property]
    ) -> ModelResult:
        ...
```

The host process can work with `LennardJones(...)`. The worker process instantiates `LennardJonesExecutor(...)` and imports ASE.

## ModelResult

`compute` returns a `ModelResult`. It is not validated at runtime, because `compute` is on the hot path. The result types contract in `atomforge-testing` checks it instead. Whatever precision the model ran in, the fields have these types:

| field | type |
|---|---|
| `energy` | `float` (`np.float64` qualifies, `np.float32` does not) |
| `forces` | float64 `numpy.ndarray`, shape `(n_atoms, 3)` |
| `stress` | float64 `numpy.ndarray`, shape `(3, 3)` |
| `energies` | float64 `numpy.ndarray`, shape `(n_atoms,)` |
| `magmoms` | float64 `numpy.ndarray`, shape `(n_atoms,)` |

Properties that were not computed are `None`. Widening float32 to float64 is exact, so a float32 model loses nothing by converting. The precision that ran is recorded in the result's provenance.

Returned arrays must not share memory with state the model reuses: a later call must not change a result returned earlier. With torch, `tensor.detach().cpu().numpy()` is a view of the tensor. `.astype(np.float64)` copies it.

Since `ModelResult` holds numpy arrays, the worker environment needs numpy. Declare it in the environment factory if the model library does not require it; torch, for example, does not.

## Supported Properties

Models advertise the properties they can compute, such as:

- `energy`
- `forces`
- `stress`
- `energies`
- `magmoms`

Tasks declare the model properties they need. Before Atomforge starts a worker calculation, the backend checks that the task's required properties are a subset of the model's supported properties. A single-point task asking for stress, for example, should fail early if the selected model only supports energy and forces.

This makes model capability part of the registry contract rather than an error discovered only after importing the model package.

## Resource Capabilities

A model declares the execution resources it can use: the accelerators it runs
on, and the numerical precisions it supports on each of them.

```python
from atomforge_core.resources.resource_caps import ResourceCapabilities

ResourceCapabilities(
    accelerator=["cpu", "cuda", "mps"],
    precision={"cpu": ["f32", "f64"], "cuda": ["f32", "f64"], "mps": ["f32"]},
)
```

Accelerators are named by backend: `cpu`, `cuda` (NVIDIA GPUs), `rocm` (AMD
GPUs) and `mps` (Apple silicon). Precisions are given per accelerator because
an accelerator may not support every precision; torch, for example, has no
float64 on MPS. A knob the model does not use is `None`, and a model that does
not use the accelerator knob gives its precisions as a plain list.

`f32` means float32 storage and computation without reduced-precision matrix
multiplication (torch's `set_float32_matmul_precision("highest")`). A model
that offers a faster mode, such as TF32 on NVIDIA GPUs, does so through a
`matmul_precision` field in its spec, which refines `f32` on `cuda` only.

Users request resources with `ExecutionResources`. Besides a backend, a
request may name `gpu`, the first of `cuda`, `rocm` and `mps` that the model
supports and the machine has, or leave a knob at `default`. The two knobs are
resolved together:

- Defaults pick the accelerator first (`cuda`, `rocm`, `mps`, `cpu`), then the
  highest precision it supports.
- An explicit precision is kept in preference to an explicit accelerator: a
  request for float64 on MPS, for a model without it there, runs on CPU in
  float64, and the result records a message.
- With `strict=True`, a request that cannot be honoured raises instead.

## Model Manifests

Models are discovered through manifests. A `ModelManifest` is the [registry](registries.md) contract for a model kind. It points Atomforge to the pieces needed to use the model:

- `kind`: the unique model identifier, such as `"ase-lj"` or a plugin model kind.
- `model_spec`: the `ModelSpec` class users instantiate.
- `executor_cls`: the worker-side `ModelExecutor` class.
- `supported_properties`: the set of properties the model can provide.
- `environment_factory_cls`: the factory that describes the model's runtime dependencies.
- `metadata`: human-facing model metadata.
- `resource_capabilities`: the accelerators and precisions the model supports (see [Resource Capabilities](#resource-capabilities)).
- `task_overrides`: optional model-specific task executors.

For a user, the manifest is usually invisible. For a model plugin author, it is the place where the model becomes discoverable by Atomforge.

## Environments

Model manifests do not directly contain a ready-made Python environment. Instead, they point to an environment factory. The backend calls that factory with the `ModelSpec`, calls the task's environment factory with the `TaskSpec`, and merges the resulting requirements into an `EnvironmentSpec`.

That resolved `EnvironmentSpec` is passed to the environment provider, which creates or reuses an isolated environment. This is what allows multiple models with incompatible dependencies to be used from the same host Python session.

## Task Overrides

Most model-backed tasks use the task's default executor. For example, `SinglePointExecutor` asks the selected model executor to compute requested properties.

Some models may need custom handling for a task. A model manifest can register a task override, mapping a task kind to a model-specific `TaskExecutor`. Atomforge's execution routing can then choose the default task executor, prefer a model override, or require one depending on the task's execution policy.

This keeps the common path simple while still allowing model-specific behavior where the generic task executor is not enough.
