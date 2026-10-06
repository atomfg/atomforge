"""Backend behaviour when workers crash, hang or are killed.

The end-to-end tests run the real worker module with the current interpreter
(no uv environment is created) and the built-in ``no-dep`` model.
"""

import os
import signal
import sys
import textwrap
from pathlib import Path

import pytest

from atomforge.backend.subprocess._environment import PreparedEnvironmentSession
from atomforge.backend.subprocess._transport import EnvSubprocess
from atomforge.backend.subprocess.backend import SubprocessBackend
from atomforge.env.base.handle import EnvironmentHandle
from atomforge.env.base.info import EnvironmentInfo
from atomforge.settings.settings import AtomforgeSettings
from atomforge_builtins.model.nodep_model import NoDep
from atomforge_builtins.task.single_point import SinglePoint
from atomforge_core.env.env import EnvironmentSpec
from atomforge_core.provenance import EnvironmentProvenance
from atomforge_core.task.spec import TaskSpec


class TaskOnlySpec(TaskSpec):
    requires_model = False
    kind: str = "task-only"

    def required_model_properties(self):
        return frozenset()


def install_session(backend, env_spec, env_subprocess) -> str:
    env_key = backend._environment_provider.environment_key(env_spec)
    session = PreparedEnvironmentSession(
        env_spec=env_spec,
        env_key=env_key,
        env_subprocess=env_subprocess,
        environment_provenance=EnvironmentProvenance(
            provider="uv", key=env_key, spec_hash=env_spec.hash()
        ),
    )
    backend.prepared_environments[env_key] = session
    backend.env_subprocesses[env_key] = env_subprocess
    return env_key


def fake_worker(script: str) -> EnvSubprocess:
    return EnvSubprocess(
        Path(sys.executable),
        name="fake",
        command=[sys.executable, "-c", textwrap.dedent(script)],
    )


def use_task_only_registry(backend, mocker, env_spec):
    registration = mocker.Mock()
    registration.has_default_executor.return_value = True
    registration.load_environment_factory.return_value = lambda task: env_spec
    backend._task_registry.get = mocker.Mock(return_value=registration)


def test_crash_during_task_is_recorded_and_worker_discarded(mocker):
    backend = SubprocessBackend()
    env_spec = EnvironmentSpec(name="crashing-env")
    use_task_only_registry(backend, mocker, env_spec)
    worker = fake_worker(
        """
        import os, sys
        sys.stdin.readline()
        sys.stderr.write("Segmentation fault in libtorch\\n")
        sys.stderr.flush()
        os._exit(139)
        """
    )
    env_key = install_session(backend, env_spec, worker)

    record = backend.try_execute(TaskOnlySpec())

    assert record.status == "error"
    assert record.phase == "task_execution"
    assert record.error.error_type == "WorkerCrashed"
    assert record.error.worker_exit_code == 139
    assert "Segmentation fault in libtorch" in record.error.worker_stderr
    assert env_key not in backend.prepared_environments
    assert env_key not in backend.env_subprocesses


def test_task_timeout_kills_worker_and_is_recorded(mocker):
    backend = SubprocessBackend()
    env_spec = EnvironmentSpec(name="hanging-env")
    use_task_only_registry(backend, mocker, env_spec)
    worker = fake_worker("import sys, time; sys.stdin.readline(); time.sleep(60)")
    env_key = install_session(backend, env_spec, worker)

    record = backend.try_execute(TaskOnlySpec(), timeout=0.5)

    assert record.status == "error"
    assert record.error.error_type == "WorkerTimeout"
    assert not worker.alive
    assert env_key not in backend.prepared_environments


def test_settings_task_timeout_is_the_default(mocker, tmp_path):
    settings = AtomforgeSettings(
        env_search_paths=(tmp_path,),
        env_install_path=tmp_path,
        worker_task_timeout_s=0.5,
    )
    backend = SubprocessBackend(settings=settings)
    env_spec = EnvironmentSpec(name="hanging-env")
    use_task_only_registry(backend, mocker, env_spec)
    install_session(
        backend,
        env_spec,
        fake_worker("import sys, time; sys.stdin.readline(); time.sleep(60)"),
    )

    record = backend.try_execute(TaskOnlySpec())

    assert record.error.error_type == "WorkerTimeout"


# --------------------------------------------------------------- end to end


@pytest.fixture
def real_worker_backend(mocker, tmp_path):
    """A backend whose environments are the current interpreter."""
    backend = SubprocessBackend(
        settings=AtomforgeSettings(
            env_search_paths=(tmp_path,), env_install_path=tmp_path
        )
    )
    handle = EnvironmentHandle(name="current", provider="uv", path=tmp_path)
    mocker.patch.object(
        backend._environment_provider, "ensure_environment", return_value=handle
    )
    mocker.patch.object(
        backend._environment_provider,
        "inspect_environment",
        return_value=EnvironmentInfo(
            handle=handle, path=tmp_path, python_executable=Path(sys.executable)
        ),
    )
    yield backend
    backend.shutdown()


def test_end_to_end_success_carries_worker_diagnostics(
    real_worker_backend, example_structure
):
    record = real_worker_backend.try_execute(
        SinglePoint(structure=example_structure), model=NoDep()
    )

    assert record.status == "success", record.error
    assert record.result.energy == pytest.approx(-0.2)
    assert record.model_preparation_diagnostics is not None
    assert record.model_preparation_diagnostics.duration_s >= 0
    assert record.task_diagnostics is not None
    assert record.task_diagnostics.duration_s >= 0


def test_end_to_end_recovers_after_worker_is_killed(
    real_worker_backend, example_structure
):
    task = SinglePoint(structure=example_structure)
    first = real_worker_backend.try_execute(task, model=NoDep())
    assert first.status == "success", first.error

    ((env_key, session),) = real_worker_backend.prepared_environments.items()
    first_process = session.env_subprocess
    os.kill(first_process._process.pid, signal.SIGKILL)
    first_process._process.wait()

    second = real_worker_backend.try_execute(task, model=NoDep())

    assert second.status == "success", second.error
    new_process = real_worker_backend.prepared_environments[env_key].env_subprocess
    assert new_process is not first_process
    assert new_process.alive
    # The model had to be initialized again in the new process.
    assert second.model_preparation_diagnostics is not None


def test_end_to_end_shutdown_stops_all_workers(real_worker_backend, example_structure):
    real_worker_backend.try_execute(
        SinglePoint(structure=example_structure), model=NoDep()
    )
    processes = list(real_worker_backend.env_subprocesses.values())
    assert processes

    real_worker_backend.shutdown()

    assert all(not process.alive for process in processes)
    assert all(process.exit_code == 0 for process in processes)
    assert not real_worker_backend.env_subprocesses
    assert not real_worker_backend.prepared_models
