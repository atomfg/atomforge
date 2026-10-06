"""Host side of the worker protocol.

Each :class:`EnvSubprocess` owns one worker process. Two background threads
drain the worker's pipes:

- stdout lines are queued, so a response can be awaited with a timeout;
- stderr is kept in a bounded ring buffer (and forwarded to the
  ``atomforge.worker`` logger), so crash and timeout errors can say *why*.

Every way a worker can fail is turned into a :class:`WorkerTransportError` subclass:

- :class:`WorkerCrashed`: the process exited, or its stdin pipe is broken.
- :class:`WorkerTimeout`: no response within the timeout. The worker is killed.
- :class:`WorkerProtocolError`: a line that is not a valid response, or a
  response to a different request. The worker is killed, because the stream
  can no longer be trusted.

Each worker runs in its own process group (a new session on POSIX, a new
process group on Windows). Killing a worker kills the whole group, so helper
processes a model started (data loaders, MPI helpers, compilers) do not outlive
it and keep holding GPU memory or inherited pipes. Processes that deliberately
start their own session escape this.

After any :class:`WorkerTransportError` the ``EnvSubprocess`` is dead (``alive`` is
False) and must be discarded; the backend starts a fresh one on next use.
"""

from __future__ import annotations

import logging
import os
import queue
import signal
import subprocess
import sys
import threading
import time
from collections import deque
from pathlib import Path
from typing import Sequence
from uuid import uuid4

from pydantic import ValidationError

from atomforge_core.protocol.core import parse_response, write_request
from atomforge_core.protocol.request import RequestMessage, ShutdownRequest
from atomforge_core.protocol.response import ResponseMessage

logger = logging.getLogger("atomforge.worker")

WORKER_MODULE = "atomforge_runtime.backend.subprocess.worker"
DEFAULT_STDERR_LINES = 200
_POLL_INTERVAL_S = 0.2
_EXIT_GRACE_S = 0.5
_EOF = None


class WorkerTransportError(RuntimeError):
    """A worker failed at the transport level. The worker is no longer usable."""

    def __init__(
        self,
        message: str,
        *,
        exit_code: int | None = None,
        stderr_tail: str | None = None,
    ) -> None:
        super().__init__(message)
        self.exit_code = exit_code
        self.stderr_tail = stderr_tail


class WorkerCrashed(WorkerTransportError):
    """The worker process exited or its pipes broke."""


class WorkerTimeout(WorkerTransportError):
    """The worker did not respond in time and was killed."""


class WorkerProtocolError(WorkerTransportError):
    """The worker sent something that is not a valid response to the request."""


def _process_group_options() -> dict:
    """Popen options that put the worker in its own process group."""
    if sys.platform == "win32":  # pragma: no cover - not tested on Windows
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


class EnvSubprocess:
    def __init__(
        self,
        executeable: Path,
        name: str,
        *,
        command: Sequence[str] | None = None,
        stderr_lines: int = DEFAULT_STDERR_LINES,
    ) -> None:
        """Start a worker.

        ``command`` replaces the default worker command
        (``<executeable> -m atomforge_runtime.backend.subprocess.worker <name>``);
        it exists for testing transport failure modes.
        """
        self.process_uuid = str(uuid4())
        self.name = name
        self._request_counter = 0
        self._executeable = Path(executeable).as_posix()
        if command is None:
            command = [self._executeable, "-m", WORKER_MODULE, name]

        self._process = subprocess.Popen(
            list(command),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            **_process_group_options(),
        )

        if (
            self._process.stdin is None
            or self._process.stdout is None
            or self._process.stderr is None
        ):  # pragma: no cover
            raise RuntimeError("Failed to open worker pipes")

        self._stdin = self._process.stdin
        self._responses: queue.Queue[str | None] = queue.Queue()
        self._stderr_tail: deque[str] = deque(maxlen=stderr_lines)

        self._stdout_thread = threading.Thread(
            target=self._drain_stdout,
            name=f"atomforge-worker-stdout-{name}",
            daemon=True,
        )
        self._stderr_thread = threading.Thread(
            target=self._drain_stderr,
            name=f"atomforge-worker-stderr-{name}",
            daemon=True,
        )
        self._stdout_thread.start()
        self._stderr_thread.start()

    # ------------------------------------------------------------------ pipes

    def _drain_stdout(self) -> None:
        assert self._process.stdout is not None
        for line in self._process.stdout:
            self._responses.put(line)
        self._responses.put(_EOF)

    def _drain_stderr(self) -> None:
        assert self._process.stderr is not None
        for line in self._process.stderr:
            line = line.rstrip("\n")
            self._stderr_tail.append(line)
            logger.debug("[%s] %s", self.name, line)

    # ----------------------------------------------------------------- status

    @property
    def alive(self) -> bool:
        return self._process.poll() is None

    @property
    def exit_code(self) -> int | None:
        return self._process.poll()

    def stderr_tail(self, wait: float = 1.0) -> str | None:
        """Most recent stderr lines. Waits briefly for the drain thread after exit."""
        if not self.alive:
            self._stderr_thread.join(timeout=wait)
        text = "\n".join(self._stderr_tail)
        return text or None

    def get_request_counter(self) -> int:
        self._request_counter += 1
        return self._request_counter

    # -------------------------------------------------------------- lifecycle

    def kill(self) -> None:
        """Kill the worker and every process in its group. Safe to call repeatedly."""
        self._kill_process_group()
        if self.alive:
            self._process.kill()
        try:
            self._process.wait(timeout=10)
        except subprocess.TimeoutExpired:  # pragma: no cover
            logger.warning("Worker %s did not exit after kill", self.name)
        self._close_stdin()

    def _kill_process_group(self) -> None:
        """SIGKILL the worker's process group, including leftover helpers.

        Also used after the worker itself has exited, to clean up helpers it
        left behind. A group with no members left is not an error.
        """
        pid = self._process.pid
        if sys.platform == "win32":  # pragma: no cover - not tested on Windows
            if self.alive:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    capture_output=True,
                    check=False,
                )
            return
        try:
            os.killpg(pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass

    def _close_stdin(self) -> None:
        try:
            self._stdin.close()
        except OSError:
            pass

    def _error(
        self, cls: type[WorkerTransportError], message: str, *, kill: bool
    ) -> WorkerTransportError:
        if kill:
            self.kill()
        else:
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
            self.kill()  # also removes helpers the crashed worker left behind
        exit_code = self.exit_code
        return cls(
            f"Worker '{self.name}': {message}"
            + (f" (exit code {exit_code})" if exit_code is not None else ""),
            exit_code=exit_code,
            stderr_tail=self.stderr_tail(),
        )

    # ---------------------------------------------------------------- request

    def request(
        self, request: RequestMessage, timeout: float | None = None
    ) -> ResponseMessage:
        """Send one request and wait for its response.

        Raises a :class:`WorkerTransportError` subclass on any transport failure.
        ``timeout`` is in seconds; ``None`` waits indefinitely.
        """
        if not self.alive:
            raise self._error(WorkerCrashed, "worker is not running", kill=False)

        try:
            write_request(self._stdin, request)
        except (BrokenPipeError, OSError, ValueError) as exc:
            raise self._error(
                WorkerCrashed,
                f"could not send {request.operation!r} request ({exc})",
                kill=False,
            ) from exc

        line = self._await_line(request, timeout)

        if line is _EOF:
            raise self._error(
                WorkerCrashed,
                f"exited while handling {request.operation!r} request",
                kill=False,
            )

        try:
            response = parse_response(line)
        except ValidationError as exc:
            snippet = line.strip()[:200]
            raise self._error(
                WorkerProtocolError,
                f"sent an invalid response to {request.operation!r} request: {snippet!r}; worker killed",
                kill=True,
            ) from exc

        if response.request_id != request.request_id:
            raise self._error(
                WorkerProtocolError,
                f"response id mismatch: expected {request.request_id}, got {response.request_id}; worker killed",
                kill=True,
            )
        return response

    def _await_line(self, request: RequestMessage, timeout: float | None) -> str | None:
        """Wait for the next stdout line, the end of stdout, or the worker's exit.

        The worker exiting is checked separately from end-of-file because a
        helper process that inherited the worker's stdout keeps the pipe open
        after the worker itself has died.
        """
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            wait = _POLL_INTERVAL_S
            if deadline is not None:
                wait = min(wait, max(0.0, deadline - time.monotonic()))
            try:
                return self._responses.get(timeout=wait)
            except queue.Empty:
                pass

            if not self.alive:
                # Give a response written just before exiting a moment to arrive.
                try:
                    return self._responses.get(timeout=_EXIT_GRACE_S)
                except queue.Empty:
                    return _EOF

            if deadline is not None and time.monotonic() >= deadline:
                raise self._error(
                    WorkerTimeout,
                    f"no response to {request.operation!r} request within {timeout} s; worker killed",
                    kill=True,
                )

    def shutdown(self, timeout: float | None = 10.0) -> ResponseMessage | None:
        """Ask the worker to exit; kill it if it does not. Never raises WorkerTransportError."""
        response = None
        if self.alive:
            request = ShutdownRequest(request_id=str(self.get_request_counter()))
            try:
                response = self.request(request, timeout=timeout)
            except WorkerTransportError as exc:
                logger.warning("%s", exc)
        self._close_stdin()
        try:
            self._process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            logger.warning("Worker %s did not exit after shutdown; killing", self.name)
        # Kill the worker if it is still running, and any helpers it left behind.
        self.kill()
        return response


def ensure_matching_response(
    request: RequestMessage, response: ResponseMessage
) -> None:
    if response.request_id != request.request_id:
        raise RuntimeError(
            f"Response id mismatch: expected {request.request_id}, "
            f"got {response.request_id}"
        )


def send_request_and_get_response(
    env_subprocess: EnvSubprocess,
    request: RequestMessage,
    timeout: float | None = None,
) -> ResponseMessage:
    return env_subprocess.request(request, timeout=timeout)


def send_shutdown_request(
    env_subprocess: EnvSubprocess, request: ShutdownRequest
) -> ResponseMessage | None:
    """Deprecated: use :meth:`EnvSubprocess.shutdown`."""
    try:
        return env_subprocess.request(request)
    except WorkerTransportError as exc:
        logger.warning("%s", exc)
        return None
