from dataclasses import dataclass

from atomforge.env.base.provider import EnvironmentProvider
from atomforge.backend.subprocess._transport import EnvSubprocess
from atomforge_core.env.env import EnvironmentSpec
from atomforge_core.model.spec import ModelSpec
from atomforge_core.provenance import EnvironmentProvenance
from atomforge_runtime.registry.model.model_registry import ModelRegistry
from atomforge_runtime.registry.task.task_registry import TaskRegistry


@dataclass
class PreparedEnvironmentSession:
    env_spec: EnvironmentSpec
    env_key: str
    env_subprocess: EnvSubprocess
    environment_provenance: EnvironmentProvenance


def setup_environment(
    *,
    model_spec: ModelSpec | None,
    task_env_spec: EnvironmentSpec,
    model_registry: ModelRegistry,
) -> EnvironmentSpec:
    if model_spec is None:
        return task_env_spec

    model_env_spec = model_registry.get(model_spec.kind).load_environment_factory()(
        model_spec
    )
    return model_env_spec + task_env_spec


def get_environment_session(
    *,
    env_spec: EnvironmentSpec,
    environment_provider: EnvironmentProvider,
    prepared_environments: dict[str, PreparedEnvironmentSession],
    env_subprocesses: dict[str, EnvSubprocess],
) -> PreparedEnvironmentSession:
    env_key = environment_provider.environment_key(env_spec)

    prepared = prepared_environments.get(env_key)
    if prepared is not None:
        return prepared

    handle = environment_provider.ensure_environment(env_spec)
    info = environment_provider.inspect_environment(handle)
    env_subprocess = EnvSubprocess(info.python_executable, name=env_key)
    environment_provenance = environment_provider.build_provenance(env_spec, handle)
    prepared = PreparedEnvironmentSession(
        env_spec=env_spec,
        env_key=env_key,
        env_subprocess=env_subprocess,
        environment_provenance=environment_provenance,
    )
    prepared_environments[env_key] = prepared
    env_subprocesses[env_key] = env_subprocess
    return prepared


def retrieve_environment_session(
    *,
    task,
    model_spec: ModelSpec | None,
    task_registry: TaskRegistry,
    model_registry: ModelRegistry,
    environment_provider: EnvironmentProvider,
    prepared_environments: dict[str, PreparedEnvironmentSession],
    env_subprocesses: dict[str, EnvSubprocess],
) -> PreparedEnvironmentSession:
    task_registration = task_registry.get(task.kind)
    task_env_spec = task_registration.load_environment_factory()(task)
    env_spec = setup_environment(
        model_spec=model_spec,
        task_env_spec=task_env_spec,
        model_registry=model_registry,
    )
    return get_environment_session(
        env_spec=env_spec,
        environment_provider=environment_provider,
        prepared_environments=prepared_environments,
        env_subprocesses=env_subprocesses,
    )
