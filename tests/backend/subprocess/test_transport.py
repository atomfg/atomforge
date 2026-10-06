"""Transport failure modes, exercised with small fake worker scripts."""

import os
import signal
import sys
import textwrap
import time
from pathlib import Path

import pytest

from atomforge.backend.subprocess._transport import (
    EnvSubprocess,
    WorkerCrashed,
    WorkerProtocolError,
    WorkerTimeout,
    WorkerTransportError,
)
from atomforge_core.protocol.request import ShutdownRequest

# Reads one request and answers it correctly, then keeps serving.
ECHO_WORKER = """
import json, sys
for line in sys.stdin:
    request = json.loads(line)
    print(json.dumps({"operation": "shutdown", "request_id": request["request_id"]}), flush=True)
    if request["operation"] == "shutdown":
        break
"""


def start(script: str) -> EnvSubprocess:
    return EnvSubprocess(
        Path(sys.executable),
        name="fake",
        command=[sys.executable, "-c", textwrap.dedent(script)],
    )


def request(request_id: str = "1") -> ShutdownRequest:
    return ShutdownRequest(request_id=request_id)


def test_successful_round_trip_and_shutdown():
    worker = start(ECHO_WORKER)
    response = worker.request(request("1"), timeout=10)
    assert response.request_id == "1"
    assert worker.alive

    worker.shutdown(timeout=10)
    assert not worker.alive
    assert worker.exit_code == 0


def test_worker_that_exits_at_startup_raises_crashed():
    worker = start("import sys; sys.stderr.write('import failed\\n'); sys.exit(3)")
    with pytest.raises(WorkerCrashed) as excinfo:
        worker.request(request(), timeout=10)

    assert excinfo.value.exit_code == 3
    assert "import failed" in excinfo.value.stderr_tail
    assert not worker.alive


def test_worker_that_dies_mid_request_reports_exit_code_and_stderr():
    worker = start(
        """
        import os, sys
        sys.stdin.readline()
        sys.stderr.write("CUDA error: out of memory\\n")
        sys.stderr.flush()
        os._exit(7)
        """
    )
    with pytest.raises(WorkerCrashed) as excinfo:
        worker.request(request(), timeout=10)

    assert excinfo.value.exit_code == 7
    assert "CUDA error: out of memory" in excinfo.value.stderr_tail
    assert "exit code 7" in str(excinfo.value)


def test_hanging_worker_times_out_and_is_killed():
    worker = start(
        """
        import sys, time
        sys.stdin.readline()
        time.sleep(60)
        """
    )
    with pytest.raises(WorkerTimeout):
        worker.request(request(), timeout=0.5)
    assert not worker.alive


def test_non_protocol_output_raises_protocol_error_and_kills_worker():
    worker = start(
        """
        import sys, time
        sys.stdin.readline()
        print("Loading model weights...", flush=True)
        time.sleep(60)
        """
    )
    with pytest.raises(WorkerProtocolError) as excinfo:
        worker.request(request(), timeout=10)
    assert "Loading model weights" in str(excinfo.value)
    assert not worker.alive


def test_response_to_wrong_request_raises_protocol_error():
    worker = start(
        """
        import json, sys, time
        sys.stdin.readline()
        print(json.dumps({"operation": "shutdown", "request_id": "other"}), flush=True)
        time.sleep(60)
        """
    )
    with pytest.raises(WorkerProtocolError, match="id mismatch"):
        worker.request(request("1"), timeout=10)
    assert not worker.alive


def test_request_to_dead_worker_raises_crashed():
    worker = start(ECHO_WORKER)
    worker.kill()
    with pytest.raises(WorkerCrashed, match="not running"):
        worker.request(request(), timeout=10)


def test_shutdown_never_raises_for_broken_workers():
    worker = start("import time; time.sleep(60)")
    worker.shutdown(timeout=0.5)  # no response, then killed
    assert not worker.alive

    worker.shutdown(timeout=0.5)  # already dead: no-op


def test_all_failures_share_a_base_class():
    for cls in (WorkerCrashed, WorkerTimeout, WorkerProtocolError):
        assert issubclass(cls, WorkerTransportError)


# ------------------------------------------------------------ process groups

SPAWN_HELPER = """
import subprocess, sys
helper = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
with open({pid_file!r}, "w") as f:
    f.write(str(helper.pid))
"""


def helper_pid(pid_file: Path) -> int:
    for _ in range(100):
        if pid_file.exists() and pid_file.read_text():
            return int(pid_file.read_text())
        time.sleep(0.05)
    raise AssertionError("helper process did not start")


def process_is_gone(pid: int, wait: float = 5.0) -> bool:
    """True once ``pid`` no longer exists or is a zombie awaiting its reaper."""
    deadline = time.monotonic() + wait
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        stat = Path(f"/proc/{pid}/stat")
        if stat.exists() and stat.read_text().split(") ")[-1].startswith("Z"):
            return True
        time.sleep(0.05)
    return False


@pytest.fixture
def spawn_helper(tmp_path):
    pid_file = tmp_path / "helper.pid"
    pids = []

    def script(rest: str) -> tuple[str, Path]:
        return SPAWN_HELPER.format(pid_file=str(pid_file)) + textwrap.dedent(
            rest
        ), pid_file

    yield script
    # Never leave stray sleepers behind, even when an assertion failed.
    if pid_file.exists() and pid_file.read_text():
        pids.append(int(pid_file.read_text()))
    for pid in pids:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX sessions")
def test_worker_runs_in_its_own_session():
    worker = start(ECHO_WORKER)
    try:
        assert os.getsid(worker._process.pid) == worker._process.pid
    finally:
        worker.kill()


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX process groups")
def test_timeout_also_kills_helper_processes(spawn_helper):
    script, pid_file = spawn_helper(
        """
        import time
        sys.stdin.readline()
        time.sleep(60)
        """
    )
    worker = start(script)
    pid = helper_pid(pid_file)

    with pytest.raises(WorkerTimeout):
        worker.request(request(), timeout=0.5)

    assert process_is_gone(pid)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX process groups")
def test_crash_also_kills_leftover_helper_processes(spawn_helper):
    script, pid_file = spawn_helper(
        """
        import os
        sys.stdin.readline()
        os._exit(1)
        """
    )
    worker = start(script)
    pid = helper_pid(pid_file)

    with pytest.raises(WorkerCrashed):
        worker.request(request(), timeout=10)

    assert process_is_gone(pid)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX process groups")
def test_clean_shutdown_also_kills_leftover_helper_processes(spawn_helper):
    script, pid_file = spawn_helper(ECHO_WORKER)
    worker = start(script)
    pid = helper_pid(pid_file)

    worker.shutdown(timeout=10)

    assert worker.exit_code == 0
    assert process_is_gone(pid)
