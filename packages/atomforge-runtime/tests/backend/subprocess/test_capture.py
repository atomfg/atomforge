import json
import subprocess
import sys
import textwrap
import warnings

from atomforge_core.protocol.request import InitModelRequest, ShutdownRequest
from atomforge_core.resources.resource_models import ExecutionResources
from atomforge_runtime.backend.subprocess.capture import capture_output


def run_python(script: str, stdin: str = "") -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(script)],
        input=stdin,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_capture_output_records_prints_and_warnings():
    with capture_output(fd_level=False) as captured:
        print("loading checkpoint")
        print("dtype downcast", file=sys.stderr)
        for _ in range(3):
            warnings.warn("element Xe not in training set", UserWarning)

    assert "loading checkpoint" in captured.output
    assert "dtype downcast" in captured.output
    assert captured.warnings == ("UserWarning: element Xe not in training set (x3)",)
    assert not captured.output_truncated


def test_capture_output_keeps_the_tail_when_truncating():
    with capture_output(fd_level=False, max_chars=10) as captured:
        print("x" * 100 + "END")

    assert captured.output_truncated
    assert captured.output.endswith("END\n")
    assert len(captured.output) == 10


def test_capture_output_is_empty_when_nothing_happens():
    with capture_output(fd_level=False) as captured:
        pass
    assert captured.output is None
    assert captured.warnings == ()


def test_isolated_protocol_stream_is_protected_from_native_writes():
    result = run_python(
        """
        import os
        from atomforge_runtime.backend.subprocess.capture import isolate_protocol_streams

        streams = isolate_protocol_streams()
        os.write(1, b"native write to fd 1\\n")
        print("python print", flush=True)
        streams.stdout.write('{"protocol": true}\\n')
        streams.stdout.flush()
        """
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == '{"protocol": true}\n'
    assert "native write to fd 1" in result.stderr
    assert "python print" in result.stderr


def test_fd_level_capture_catches_native_output():
    result = run_python(
        """
        import json, os
        from atomforge_runtime.backend.subprocess.capture import (
            capture_output, isolate_protocol_streams,
        )

        streams = isolate_protocol_streams()
        with capture_output(fd_level=True) as captured:
            os.write(1, b"native stdout\\n")
            os.write(2, b"native stderr\\n")
            print("python stdout")
        os.write(2, b"after capture\\n")
        streams.stdout.write(json.dumps({"output": captured.output}) + "\\n")
        streams.stdout.flush()
        """
    )
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)["output"]
    assert "native stdout" in output
    assert "native stderr" in output
    assert "python stdout" in output
    assert "after capture" not in output
    assert "after capture" in result.stderr


def test_worker_main_answers_on_isolated_stream():
    request = ShutdownRequest(request_id="42").model_dump_json() + "\n"
    result = run_python(
        """
        import sys
        from atomforge_runtime.backend.subprocess.worker import main
        sys.exit(main("test"))
        """,
        stdin=request,
    )
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["request_id"] == "42"


def test_init_and_task_responses_carry_diagnostics(worker):
    response, _ = worker._handle_request(
        InitModelRequest(
            request_id="diag-1",
            model_kind="fake-model",
            model_payload={"kind": "fake-model"},
            exec_resources=ExecutionResources(),
        )
    )
    assert response.operation == "init_model"
    assert response.diagnostics is not None
    assert response.diagnostics.duration_s >= 0


def test_init_failure_carries_diagnostics(worker):
    response, _ = worker._handle_request(
        InitModelRequest(
            request_id="diag-2",
            model_kind="unknown_model",
            model_payload={},
            exec_resources=ExecutionResources(),
        )
    )
    assert response.operation == "error"
    assert response.diagnostics is not None


def test_distinct_warnings_are_capped():
    from atomforge_runtime.backend.subprocess.capture import MAX_DISTINCT_WARNINGS

    with capture_output(fd_level=False) as captured:
        for i in range(MAX_DISTINCT_WARNINGS + 500):
            warnings.warn(f"step {i}: energy drift", RuntimeWarning)

    assert len(captured.warnings) == MAX_DISTINCT_WARNINGS + 1
    assert captured.warnings[-1] == "... 500 further warnings omitted"


def test_python_output_buffer_stays_bounded():
    from atomforge_runtime.backend.subprocess import capture

    max_chars = 1_000
    with capture_output(fd_level=False, max_chars=max_chars) as captured:
        buffer = sys.stdout
        for i in range(100_000):
            print(f"step {i}")
            assert len(buffer.getvalue()) <= 2 * max_chars + 20

    assert isinstance(buffer, capture._TailBuffer)
    assert captured.output_truncated
    assert len(captured.output) == max_chars
    assert captured.output.endswith("step 99999\n")


def test_fd_level_capture_reads_only_the_tail_of_large_native_output():
    result = run_python(
        """
        import json, os
        from atomforge_runtime.backend.subprocess.capture import (
            capture_output, isolate_protocol_streams,
        )

        streams = isolate_protocol_streams()
        with capture_output(fd_level=True, max_chars=1000) as captured:
            chunk = b"x" * 1_000_000
            for _ in range(5):
                os.write(1, chunk)
            os.write(1, b"END\\n")
        streams.stdout.write(
            json.dumps({"output": captured.output, "truncated": captured.output_truncated})
            + "\\n"
        )
        streams.stdout.flush()
        """
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["truncated"]
    assert len(payload["output"]) == 1000
    assert payload["output"].endswith("END\n")
