from dataclasses import dataclass
from typing import Callable

from atomforge.backend.subprocess._environment import PreparedEnvironmentSession
from atomforge.backend.subprocess._transport import EnvSubprocess
from atomforge_core.model.spec import ModelSpec
from atomforge_core.protocol.request import InitModelRequest
from atomforge_core.protocol.response import InitModelResponse
from atomforge_core.protocol.session import model_session_key
from atomforge_core.resources.resource_models import (
    ExecutionResources,
    ResolvedResources,
)
from atomforge_core.task.spec import TaskSpec


@dataclass
class PreparedModelSession:
    model_spec: ModelSpec
    model_session_id: str
    execution_resources: ExecutionResources
    resolved_resources: ResolvedResources
    process_uuid: str


def prepare_init_model_request(
    *,
    model_spec: ModelSpec,
    exec_resources: ExecutionResources,
    env_subprocess: EnvSubprocess,
) -> InitModelRequest:
    return InitModelRequest(
        request_id=str(env_subprocess.get_request_counter()),
        model_kind=model_spec.kind,
        model_payload=model_spec.model_dump(),
        exec_resources=exec_resources,
    )


def retrieve_prepared_model_session(
    *,
    model_spec: ModelSpec,
    task: TaskSpec,
    exec_resources: ExecutionResources,
    env_session: PreparedEnvironmentSession,
    prepared_models: dict[tuple[str, str], PreparedModelSession],
    prepare_model: Callable[[ModelSpec, TaskSpec, ExecutionResources], None],
) -> PreparedModelSession:
    model_cache_key = model_session_key(model_spec, exec_resources)
    env_cache_key = env_session.env_key
    prepared = prepared_models.get((model_cache_key, env_cache_key))

    if (
        prepared is None
        or prepared.process_uuid != env_session.env_subprocess.process_uuid
    ):
        prepared_models.pop((model_cache_key, env_cache_key), None)
        prepare_model(model_spec, task, exec_resources)
        prepared = prepared_models[(model_cache_key, env_cache_key)]
    return prepared


def cache_prepared_model_session(
    *,
    model_spec: ModelSpec,
    exec_resources: ExecutionResources,
    env_session: PreparedEnvironmentSession,
    response: InitModelResponse,
    prepared_models: dict[tuple[str, str], PreparedModelSession],
) -> None:
    model_cache_key = model_session_key(model_spec, exec_resources)
    prepared_models[(model_cache_key, env_session.env_key)] = PreparedModelSession(
        model_spec=model_spec,
        model_session_id=response.model_session_id,
        execution_resources=exec_resources,
        resolved_resources=response.resolved_resources,
        process_uuid=env_session.env_subprocess.process_uuid,
    )
