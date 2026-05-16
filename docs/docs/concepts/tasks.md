# Tasks

A task describes what should be computed. It does not describe which model should be used, and it does not directly perform the computation. That separation lets the same task be run with different models and lets Atomforge validate whether a model can satisfy the task before starting the worker calculation.

Atomforge splits task behavior into four main pieces:

- `TaskSpec`: the user-facing input specification.
- `TaskExecutor`: the worker-side implementation.
- `TaskResult`: the serializable result object returned to the host.
- `TaskManifest`: the [registry](registries.md) contract that connects a task kind to its spec, executor, result, capabilities, and environment.

## TaskSpec

A `TaskSpec` is a Pydantic model that describes the requested computation. It is serializable and can cross the subprocess boundary.

The built-in single-point task is a model-backed task. It asks a model to compute selected properties for one structure:

```python
from atomforge_builtins.task.single_point import SinglePoint
from atomforge_core.structure import StructureData

structure = StructureData(
    positions=[[0, 0, 0], [1, 0, 0]],
    numbers=[1, 1],
    cell=[[5, 0, 0], [0, 5, 0], [0, 0, 5]],
    pbc=[False, False, False],
)

task = SinglePoint(
    structure=structure,
    properties=["energy", "forces"],
)
```

`SinglePoint` stores the structure and requested properties. It does not import or initialize any model package. It only describes the calculation.

## Required Model Properties

Model-backed tasks declare which model properties they require with `required_model_properties()`.

For `SinglePoint`, the required properties are the properties requested by the user. If the task asks for energy and forces, the selected model must support energy and forces. If it asks for stress, the selected model must support stress too.

The backend checks this on the host side before preparing the worker execution. This gives early, clear incompatibility errors when a task/model pair cannot work.

## Model-Backed and Model-Free Tasks

Most atomistic prediction tasks require a model. `SinglePoint`, `BatchSinglePoint`, `BFGS`, and structure optimization tasks are model-backed because they need model energies, forces, or stresses.

Some tasks are model-free. `AnalyzeSymmetry` is an example: it analyzes crystallographic symmetry from the structure using its own task environment and does not need a model executor.

Model-free tasks set:

```python
requires_model = False
```

and return an empty set from `required_model_properties()`. Atomforge validates this distinction:

- a model-backed task must be given a model;
- a model-free task must not be given a model;
- a model-free task cannot require a model override.

## TaskExecutor

A `TaskExecutor` is instantiated in the worker environment. It receives the task spec and a `TaskExecutionContext`.

For model-backed tasks, the context contains a prepared model executor. The single-point executor follows the common pattern:

```python
class SinglePointExecutor:
    def execute(self, spec, context):
        model_executor = require_model_executor(context, task_kind=spec.kind)
        model_result = model_executor.compute(spec.structure, spec.properties)
        return SinglePointResult(
            energy=model_result.energy,
            forces=model_result.forces,
            stress=model_result.stress,
            magmoms=model_result.magmoms,
            energies=model_result.energies,
        )
```

The task executor owns task-level behavior. The model executor owns model-level prediction. This is why a task can be reused across many models.

## TaskResult

Each task has a result model. For `SinglePoint`, the result can contain energy, forces, stress, magnetic moments, and per-atom energies:

```python
class SinglePointResult(TaskResult):
    kind: Literal["single_point"]
    energy: float | None
    forces: list[list[float]] | None
    stress: list[list[float]] | None
    magmoms: list[float] | None
    energies: list[float] | None
```

Successful backend executions attach provenance to the returned `TaskResult`. That provenance records the task payload, model payload, environment information, requested and resolved resources, and execution timing.

## Task Manifests

Tasks are discovered through manifests. A `TaskManifest` connects a task kind to the components Atomforge needs:

- `kind`: the unique task identifier.
- `spec_model`: the `TaskSpec` class.
- `executor_cls`: the default worker-side `TaskExecutor`, if one exists.
- `result_model`: the `TaskResult` class.
- `capability_spec`: task capability metadata.
- `environment_factory_cls`: the factory that describes task-side runtime dependencies.

The manifest is usually invisible to users running tasks. It matters when adding a task plugin, because the manifest is what lets the [task registry](registries.md) find and validate the task.

## Execution Routes and Model Overrides

When a task is executed with a model, Atomforge resolves an execution route. The default route uses the task's registered executor. A model can also provide a task override when it needs custom task behavior.

The task's `ExecutionPolicy` controls how this works:

- `DEFAULT`: use the normal task executor when available.
- `PREFER_MODEL_OVERRIDE`: prefer a model-specific task executor if one exists.
- `REQUIRE_MODEL_OVERRIDE`: require the selected model to provide a task-specific executor.

Most users do not need to set this explicitly. It is mainly useful when a task has both a generic implementation and model-specific optimized or specialized implementations.
