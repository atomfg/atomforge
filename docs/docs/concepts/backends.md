# Backends

A backend is responsible for turning a task and, optionally, a model into an executed calculation. It plans the calculation on the host side, prepares or reuses an isolated worker environment, communicates with the worker process, validates the result, and returns a `TaskResult`.

The main concrete backend today is `SubprocessBackend`.

## What the Backend Does

At a high level, a backend connects three things:

- a `TaskSpec`, which describes what should be computed;
- an optional `ModelSpec`, which describes which model configuration should be used;
- an isolated worker environment, where task and model executors can import their runtime dependencies.

A minimal execution looks like this:

```python
from atomforge.backend.subprocess import SubprocessBackend
from atomforge_builtins.model.ase_lj import LennardJones
from atomforge_builtins.task.single_point import SinglePoint

task = SinglePoint(structure=structure, properties=["energy", "forces"])
model = LennardJones()

with SubprocessBackend() as backend:
    result = backend.execute(task, model)

print(result.energy)
print(result.provenance)
```

The user-facing call is small, but the backend does several pieces of coordination before the task runs.

## Host-Side Planning

Before a task is sent to a worker, the backend validates the request on the host side.

It checks that:

- model-backed tasks are given a model;
- model-free tasks are not given a model;
- the task kind is registered in the [task registry](registries.md);
- the model kind is registered in the [model registry](registries.md), when a model is present;
- the selected model supports the properties required by the task;
- an execution route exists, either through the task's default executor or a model-specific task override.

This planning step catches many incompatibilities before Atomforge creates an environment or imports model dependencies.

## Environment Resolution

Tasks and models each define environment requirements through registered environment factories. The backend calls those factories and resolves the result into an `EnvironmentSpec`.

For a model-backed task, the effective environment is the combination of:

- the task environment, such as task-side dependencies needed by the task executor;
- the model environment, such as the MLIP package and its runtime dependencies.

For a model-free task, only the task environment is needed.

The environment provider then creates or reuses an environment matching that `EnvironmentSpec`. The default provider kind is currently based on `uv`.

## Worker Processes

`SubprocessBackend` runs computations in worker subprocesses. Each prepared environment has an associated worker process, and the backend keeps a cache of prepared environments and subprocesses while the backend object is alive.

The host process sends serialized requests to the worker. The worker loads the registered task and model components from inside the isolated environment, performs the computation, and sends a serialized response back.

The important user-facing consequence is that model dependencies are isolated from the host Python environment. A package needed by MACE, CHGNet, Orb, or another model is loaded in that model's worker environment rather than in the process where the user wrote their script.

## Model Session Reuse

Some models are expensive to initialize. `SubprocessBackend` keeps prepared model sessions keyed by the model specification, execution resources, and environment.

When the same backend object runs another compatible task with the same model and resources, it can reuse the prepared model session instead of initializing the model again. If the worker process changes, the cached model session is discarded and prepared again.

This is why long-running workflows should reuse a backend instance:

```python
backend = SubprocessBackend()
model = LennardJones()

for structure in structures:
    task = SinglePoint(structure=structure, properties=["energy"])
    result = backend.execute(task, model)
```

## Results and Provenance

The worker returns a serialized task result payload. The backend validates that payload against the task's registered result model and attaches provenance before returning the `TaskResult`.

Successful results carry provenance describing:

- the task kind and payload hash;
- the model kind and payload hash, when a model was used;
- the environment provider, environment key, and environment spec hash;
- requested and resolved execution resources;
- execution timing.

This provenance is attached to the result returned by `execute()`.

## `execute()` and `try_execute()`

`SubprocessBackend` exposes two execution styles.

Use `execute()` when you want the normal result-returning API:

```python
result = backend.execute(task, model)
```

If validation or execution fails, `execute()` raises an exception. Input validation and incompatibility failures are raised as `ValueError`; other backend or worker failures are raised as `RuntimeError`.

Use `try_execute()` when you want a record-oriented API:

```python
record = backend.try_execute(task, model)
if record.status == "success":
    result = record.result
else:
    print(record.phase)
    print(record.error)
```

`try_execute()` returns an `ExecutionRecord` for both success and failure. Successful records contain the result and full provenance. Failed records contain an error and either full or partial provenance, depending on how far execution progressed.

## Failure Phases

When using `try_execute()`, failures are reported with a phase. The main phases are:

- `input_validation`: the task/model request is invalid before environment preparation.
- `environment_preparation`: the environment could not be resolved, created, inspected, or started.
- `model_preparation`: the worker could not initialize the model session.
- `task_execution`: the worker could not execute the task, or reported task/model incompatibility.
- `result_validation`: the worker returned a payload that did not validate as the registered result model.

These phases are intended to make backend failures inspectable without forcing users to parse worker tracebacks or environment logs first.
