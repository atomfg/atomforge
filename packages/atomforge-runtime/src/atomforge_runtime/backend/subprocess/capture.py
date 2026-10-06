"""Output isolation and capture for the subprocess worker.

Two separate problems are solved here:

1. Protecting the protocol channel. The worker talks to the host with JSON
   lines on stdout. Model libraries can write to file descriptor 1 directly
   (C/C++/CUDA extensions, child processes), which bypasses
   ``contextlib.redirect_stdout`` and would corrupt the protocol stream.
   :func:`isolate_protocol_streams` moves the protocol onto private duplicates
   of fds 0 and 1 and points fd 1 at stderr, so nothing else can reach it.

2. Keeping what models say. Warnings and log output are scientific data for a
   benchmark (e.g. "element not in training set"). :func:`capture_output`
   records Python warnings and all stdout/stderr output produced while
   handling one request, at both the Python and the file-descriptor level.
"""

from __future__ import annotations

import contextlib
import ctypes
import io
import os
import sys
import tempfile
import warnings
from collections import Counter
from dataclasses import dataclass, field
from typing import Iterator, TextIO

DEFAULT_MAX_OUTPUT_CHARS = 20_000
MAX_DISTINCT_WARNINGS = 50


@dataclass(frozen=True)
class ProtocolStreams:
    stdin: TextIO
    stdout: TextIO
    crash_stream: TextIO


def isolate_protocol_streams() -> ProtocolStreams:
    """Move the protocol onto private file descriptors.

    After this call:

    - the returned ``stdin``/``stdout`` are the only handles on the pipes to
      the host;
    - fd 0 reads from ``/dev/null`` and fd 1 writes to stderr, so anything a
      model prints (from Python or native code) ends up on stderr instead of
      in the protocol stream;
    - ``faulthandler`` writes Python tracebacks for hard crashes (segfaults,
      aborts) to a private duplicate of stderr that is not affected by
      per-request capture, so the host can report them.

    Must be called once, at worker start-up, before anything else writes.
    """
    import faulthandler

    sys.stdout.flush()
    sys.stderr.flush()

    protocol_in_fd = os.dup(0)
    protocol_out_fd = os.dup(1)

    devnull_fd = os.open(os.devnull, os.O_RDONLY)
    os.dup2(devnull_fd, 0)
    os.close(devnull_fd)
    os.dup2(2, 1)

    crash_stream = os.fdopen(os.dup(2), "w", encoding="utf-8", buffering=1)
    faulthandler.enable(file=crash_stream)

    return ProtocolStreams(
        stdin=os.fdopen(protocol_in_fd, "r", encoding="utf-8"),
        stdout=os.fdopen(protocol_out_fd, "w", encoding="utf-8"),
        crash_stream=crash_stream,
    )


@dataclass
class CapturedOutput:
    """Filled in when the :func:`capture_output` block exits."""

    output: str | None = None
    output_truncated: bool = False
    warnings: tuple[str, ...] = field(default_factory=tuple)


def _flush_c_stdio() -> None:
    """Flush C-level stdio buffers so native output lands before fds are restored."""
    try:
        ctypes.CDLL(None).fflush(None)
    except Exception:  # pragma: no cover - platform dependent
        pass


class _WarningCounter:
    """Counts warnings by text. Memory is bounded by ``MAX_DISTINCT_WARNINGS``."""

    def __init__(self) -> None:
        self.counts: Counter[str] = Counter()
        self.omitted = 0

    def showwarning(self, message, category, filename, lineno, file=None, line=None):
        text = f"{category.__name__}: {message}"
        if text in self.counts or len(self.counts) < MAX_DISTINCT_WARNINGS:
            self.counts[text] += 1
        else:
            self.omitted += 1

    def summary(self) -> tuple[str, ...]:
        summary = [
            text if count == 1 else f"{text} (x{count})"
            for text, count in self.counts.items()
        ]
        if self.omitted:
            summary.append(f"... {self.omitted} further warnings omitted")
        return tuple(summary)


class _TailBuffer(io.TextIOBase):
    """Text sink that keeps only the last ``max_chars`` characters written."""

    def __init__(self, max_chars: int) -> None:
        self._max_chars = max_chars
        self._text = ""
        self.truncated = False

    def writable(self) -> bool:
        return True

    def write(self, text: str) -> int:
        self._text += text
        if len(self._text) > 2 * self._max_chars:
            self._text = self._text[-self._max_chars :]
            self.truncated = True
        return len(text)

    def getvalue(self) -> str:
        return self._text


def _read_tail(file, max_chars: int) -> tuple[str, bool]:
    """Read at most the last ~``max_chars`` characters of a binary file."""
    max_bytes = 4 * max_chars  # UTF-8 uses at most 4 bytes per character
    size = file.seek(0, os.SEEK_END)
    file.seek(max(0, size - max_bytes))
    return file.read().decode("utf-8", errors="replace"), size > max_bytes


def _tail(text: str, max_chars: int, truncated: bool) -> tuple[str | None, bool]:
    if not text:
        return None, False
    if len(text) <= max_chars:
        return text, truncated
    return text[-max_chars:], True


@contextlib.contextmanager
def capture_output(
    *, fd_level: bool, max_chars: int = DEFAULT_MAX_OUTPUT_CHARS
) -> Iterator[CapturedOutput]:
    """Capture warnings and output produced inside the block.

    With ``fd_level=False`` only Python-level ``sys.stdout``/``sys.stderr``
    writes are captured; this is safe to use in-process (e.g. in tests).
    With ``fd_level=True`` file descriptors 1 and 2 are also redirected, which
    catches output from native code. Only use that in the worker process.

    Memory use is bounded: only the last ``max_chars`` characters of output and
    at most ``MAX_DISTINCT_WARNINGS`` distinct warnings are kept. Native output
    is spooled to an anonymous temporary file, so disk use is *not* bounded
    within a single request; a model that writes gigabytes per request should
    be silenced at the source.
    """
    captured = CapturedOutput()
    python_buffer = _TailBuffer(max_chars)
    warning_counter = _WarningCounter()

    with contextlib.ExitStack() as stack:
        stack.enter_context(warnings.catch_warnings())
        warnings.simplefilter("always")
        warnings.showwarning = warning_counter.showwarning

        tmp = None
        saved_fds: tuple[int, int] | None = None
        if fd_level:
            tmp = stack.enter_context(tempfile.TemporaryFile(mode="w+b"))
            sys.stdout.flush()
            sys.stderr.flush()
            saved_fds = (os.dup(1), os.dup(2))
            os.dup2(tmp.fileno(), 1)
            os.dup2(tmp.fileno(), 2)

        try:
            with (
                contextlib.redirect_stdout(python_buffer),
                contextlib.redirect_stderr(python_buffer),
            ):
                yield captured
        finally:
            fd_text, fd_truncated = "", False
            if saved_fds is not None and tmp is not None:
                _flush_c_stdio()
                os.dup2(saved_fds[0], 1)
                os.dup2(saved_fds[1], 2)
                os.close(saved_fds[0])
                os.close(saved_fds[1])
                fd_text, fd_truncated = _read_tail(tmp, max_chars)

            text = python_buffer.getvalue() + fd_text
            captured.output, captured.output_truncated = _tail(
                text, max_chars, python_buffer.truncated or fd_truncated
            )
            captured.warnings = warning_counter.summary()
