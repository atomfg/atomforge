# Registries

Registries are Atomforge's discovery layer. They let installed packages contribute models and tasks without hard-coding imports in the backend or in user code.

There are two main registries:

- `ModelRegistry`, which discovers model kinds.
- `TaskRegistry`, which discovers task kinds.

Most users meet registries indirectly. When a backend receives a `TaskSpec` and an optional `ModelSpec`, it uses the task and model `kind` fields to look up the registered components needed to validate and execute the calculation.

## Entry Points

Atomforge discovers plugins through Python package entry points. A package exposes a manifest object under an Atomforge entry-point group:

- `atomforge.model` for models.
- `atomforge.task` for tasks.

A model package can expose a model like this:

```toml
[project.entry-points.'atomforge.model']
ase-lj = "atomforge_builtins.model.ase_lj.manifest:lennard_jones_manifest"
```

The entry point points to a manifest object. It should not need to instantiate the model executor or import heavy runtime dependencies just to make the model discoverable.

Task packages use the same pattern with the task entry-point group:

```toml
[project.entry-points.'atomforge.task']
single-point = "atomforge_builtins.task.single_point.manifest:single_point_manifest"
```

## Manifests and Registrations

A manifest is the package-authored declaration. It says, "this package provides a model or task with this kind, and here are the dotted paths to the pieces Atomforge needs."

A registration is the runtime object built from that manifest. Registrations are what the backend and worker use after discovery.

This distinction matters because manifests are mostly declarations, while registrations know how to load and validate the referenced symbols when they are needed.

For example, a model manifest includes paths to:

- the model spec class;
- the model executor class;
- supported properties;
- the environment factory;
- model metadata;
- resource capabilities;
- optional model-specific task overrides.

The corresponding model registration stores these paths and loads many of them lazily. This keeps registry startup light and avoids importing model runtime packages earlier than necessary.

Task manifests follow the same pattern. A task manifest points to:

- the task spec class;
- the task result model;
- the default task executor, if one exists;
- the task capability spec;
- the task environment factory.

## Model Registry

`ModelRegistry.default()` scans the `atomforge.model` entry-point group, loads each model manifest, converts it into a `ModelRegistration`, and indexes the registration by model kind.

The model kind is the value used by `ModelSpec.kind`. For example, a `LennardJones` spec has kind `"ase-lj"`, so the backend can look up the registration for `"ase-lj"` when that model is passed to `execute()`.

A `ModelRegistration` gives Atomforge access to the model pieces needed at different stages:

- host-side compatibility checks use supported properties;
- environment resolution uses the model environment factory;
- worker-side model setup uses the model executor class;
- resource handling uses resource capabilities and optional probes;
- execution routing can inspect model-specific task overrides.

The registry does not mean every model dependency is imported on startup. The registration can load individual pieces when the backend or worker needs them.

## Task Registry

`TaskRegistry.default()` scans the `atomforge.task` entry-point group, loads each task manifest, converts it into a `TaskRegistration`, and indexes the registration by task kind.

The task kind is the value stored on a `TaskSpec`. For example, `SinglePoint` uses the `"single_point"` task kind. When the backend receives that task, it asks the task registry for the matching registration.

A `TaskRegistration` gives Atomforge access to:

- the task spec model;
- the task result model;
- the default task executor class, if one exists;
- the task capability spec;
- the task environment factory.

Some tasks have a default executor that works for many models. Other tasks may rely on model-specific task overrides. The task registry and model registry provide the information needed to choose the execution route.

## How Backends Use Registries

Backends use registries during planning and execution.

On the host side, `SubprocessBackend` uses the registries to:

- look up the task registration from `task.kind`;
- look up the model registration from `model.kind`, when a model is present;
- check whether the model supports the properties required by the task;
- resolve whether execution should use the default task executor or a model override;
- load the task and model environment factories to build the effective `EnvironmentSpec`.

After the worker returns a response, the backend uses the task registration again to load the registered result model and validate the returned result payload.

The worker process also has registries. Inside the isolated environment, the worker uses them to load the executor classes and other registered components from packages installed in that environment.

## Validation Modes

Registries have two useful loading modes.

`default()` loads entry points and performs lightweight registration. It confirms that each entry point returns the expected manifest type and that the manifest can be converted into a registration. This is the normal path used by backends.

`strict()` goes further. After loading registrations, it asks each registration to load and validate its referenced symbols. For a model registration, that includes symbols such as metadata, executor class, supported properties, environment factory, resource capabilities, probes, and task override executors.

Strict validation is useful when testing a plugin or diagnosing a broken installation. It catches problems such as:

- an unknown or duplicate kind;
- an entry point that does not return the expected manifest type;
- a manifest whose `distribution` does not match the package that exposes the entry point;
- a dotted path that points to a missing module or symbol;
- a referenced symbol with the wrong type.

Normal execution does not need to eagerly load every registered symbol. Lazy loading is part of how Atomforge keeps host-side discovery lightweight while still validating components before they are used.
