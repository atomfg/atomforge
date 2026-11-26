"""A fake `uv` for tests of environment handling, so that no environment is
really built."""

import subprocess
from pathlib import Path


class FakeUv:
    """Stands in for `subprocess.run` in the uv provider; other commands
    than uv run for real.

    `uv sync` creates `.venv/bin/python` and `uv.lock` in its working
    directory, or fails if `sync_fails`. `uv sync --check` returns
    `check_returncode`.
    """

    def __init__(self, run):
        self._run = run
        self.calls: list[tuple[list[str], Path]] = []
        self.sync_fails = False
        self.check_returncode = 0

    def __call__(self, command, *args, cwd=None, check=False, **kwargs):
        command = list(command)
        if command[0] != "uv":
            return self._run(command, *args, cwd=cwd, check=check, **kwargs)
        cwd = Path(cwd)
        self.calls.append((command, cwd))
        if "sync" not in command:
            raise AssertionError(f"unexpected uv command: {command}")

        if "--check" in command:
            returncode = self.check_returncode
        elif self.sync_fails:
            returncode = 1
        else:
            python = cwd / ".venv" / "bin" / "python"
            python.parent.mkdir(parents=True, exist_ok=True)
            python.write_text("")
            (cwd / "uv.lock").write_text("lock")
            returncode = 0

        if check and returncode != 0:
            raise subprocess.CalledProcessError(returncode, command)
        return subprocess.CompletedProcess(command, returncode, "", "")

    def syncs(self) -> list[Path]:
        return [cwd for command, cwd in self.calls if "--check" not in command]

    def checks(self) -> list[Path]:
        return [cwd for command, cwd in self.calls if "--check" in command]


def install_fake_uv(monkeypatch) -> FakeUv:
    fake = FakeUv(subprocess.run)
    monkeypatch.setattr("atomforge.env.uv.uv.subprocess.run", fake)
    return fake
