import json
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from atomforge_core.env.env import EnvironmentSpec

from atomforge.env.base.handle import EnvironmentHandle
from atomforge.env.base.info import EnvironmentInfo
from atomforge.env.base.provider import (
    EnvironmentMarker,
    EnvironmentProvider,
    file_sha256,
)
from atomforge.env.base.resolution import EnvironmentResolutionResult
from atomforge.env.uv.uv_pyproject_writer import UVPyprojectWriter
from atomforge.env.base.dependency import ResolvedDependency
import hashlib

logger = logging.getLogger(__name__)


class UVEnvironmentProvider(EnvironmentProvider):
    provider_name = "uv"

    def __init__(
        self,
        search_path: tuple[Path, ...],
        install_path: Path,
        *,
        warn_when_building: bool = True,
    ):
        super().__init__(
            search_path, install_path, warn_when_building=warn_when_building
        )
        self._core_resolved = ResolvedDependency(
            requirement="atomforge-core", exact=True
        )
        self._runtime_resolved = ResolvedDependency(
            requirement="atomforge-runtime", exact=True
        )
        self._internal_package_fingerprint = (
            self._core_resolved.fingerprint + self._runtime_resolved.fingerprint
        )

    def environment_key(self, spec: EnvironmentSpec) -> str:
        environment_key = hashlib.sha256(
            json.dumps(
                {
                    "spec": spec.hash(),
                    "provider": self.provider_name,
                    "internal_packages": self._internal_package_fingerprint,
                    "schema": 1,
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()[0:16]

        return environment_key

    def ensure_environment(self, spec: EnvironmentSpec) -> EnvironmentHandle:
        env_key = self.environment_key(spec)

        handle = self._search_for_environment(env_key)
        if handle:
            return handle

        self.prepare_install_path()
        # Write the pyproject.toml for the environment:
        project_path = self.install_path / self.provider_name / env_key
        project_path.mkdir(parents=True, exist_ok=True)
        self._write_pyproject(spec, project_path / "pyproject.toml")

        # Sync the environment:
        command = [
            "uv",
            "-q",
            "sync",
        ]
        if self.warn_when_building and self.preloaded_paths:
            logger.warning(
                "Environment %s (key %s) is not in the preloaded search paths "
                "(%s); building it at run time in %s",
                spec.name,
                env_key,
                ", ".join(str(p) for p in self.preloaded_paths),
                project_path,
            )
        result = subprocess.run(command, check=True, cwd=project_path)

        if result.returncode != 0:
            raise RuntimeError(f"Failed to create environment: {result}")

        EnvironmentMarker(
            key=env_key,
            name=spec.name,
            spec_hash=spec.hash(),
            lockfile_hash=file_sha256(project_path / "uv.lock"),
        ).write(project_path)

        return EnvironmentHandle(
            path=project_path, name=spec.name, provider=self.provider_name
        )

    def resolve_environment(self, spec: EnvironmentSpec) -> EnvironmentResolutionResult:
        command = ("uv", "sync", "--dry-run", "--no-progress")
        self.prepare_install_path()
        project_path = Path(
            tempfile.mkdtemp(prefix="atomforge-env-resolve-", dir=self.install_path)
        )
        self._write_pyproject(spec, project_path / "pyproject.toml")
        result = subprocess.run(
            command,
            check=False,
            cwd=project_path,
            capture_output=True,
            text=True,
        )
        success = result.returncode == 0
        if success:
            shutil.rmtree(project_path)

        return EnvironmentResolutionResult(
            provider=self.provider_name,
            success=success,
            message=(
                None
                if success
                else f"uv dry-run resolution failed with exit code {result.returncode}"
            ),
            stdout=result.stdout,
            stderr=result.stderr,
            project_path=project_path,
            command=command,
        )

    def _check_environment(self, handle: EnvironmentHandle) -> bool:
        command = [
            "uv",
            "-q",
            "sync",
            "--check",
        ]
        result = subprocess.run(
            command, check=False, capture_output=True, text=True, cwd=handle.path
        )
        return result.returncode == 0

    def inspect_environment(self, handle: EnvironmentHandle) -> EnvironmentInfo:
        env_path = handle.path
        python_executable = env_path / ".venv" / "bin" / "python"
        exists = env_path.exists() and python_executable.exists()
        return EnvironmentInfo(
            handle=handle,
            path=env_path,
            python_executable=python_executable if exists else None,
        )

    def build_provenance(
        self,
        spec: EnvironmentSpec,
        handle: EnvironmentHandle | None = None,
    ):
        provenance = super().build_provenance(spec, handle)
        if handle is None:
            return provenance

        return provenance.model_copy(
            update={
                "pyproject_hash": file_sha256(handle.path / "pyproject.toml"),
                "lockfile_hash": file_sha256(handle.path / "uv.lock"),
            }
        )

    def remove_environment(self, handle: EnvironmentHandle) -> None:
        env_path = handle.path
        if env_path.exists():
            result = subprocess.run(["rm", "-rf", env_path.as_posix()], check=True)
            if result.returncode != 0:
                raise RuntimeError(f"Failed to remove environment: {result}")

    def _write_pyproject(self, spec: EnvironmentSpec, path: Path) -> None:
        provider_requirements = [
            ResolvedDependency(req, exact=True) for req in spec.provider_requirements
        ]
        atomforge_requirements = [self._runtime_resolved, self._core_resolved]
        spec_requirements = [
            ResolvedDependency(req, exact=False) for req in spec.requirements
        ]
        all_requirements = (
            provider_requirements + atomforge_requirements + spec_requirements
        )
        writer = UVPyprojectWriter(
            env_name=spec.name,
            python_version=spec.python,
            dependencies=list(all_requirements),
            extras=spec.extras,
        )
        writer.write(path)

    def _search_for_environment(self, env_key: str) -> EnvironmentHandle | None:
        for path in self.search_paths:
            candidate = path / self.provider_name / env_key
            if not candidate.exists():
                continue
            handle = EnvironmentHandle(
                path=candidate, name=env_key, provider=self.provider_name
            )
            if not self.is_install_path(path):
                # Preloaded: trusted by its marker, never checked or removed.
                marker = EnvironmentMarker.read(candidate)
                python = self.inspect_environment(handle).python_executable
                if marker is not None and marker.key == env_key and python:
                    return handle
                logger.debug(
                    "Skipping %s: not a complete preloaded environment", candidate
                )
                continue
            if self._check_environment(handle):
                return handle
            # An invalid environment in the install path is removed and rebuilt.
            self.remove_environment(handle)
        return None
