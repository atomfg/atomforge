from atomforge.env.base.handle import EnvironmentHandle
from atomforge.env.base.info import EnvironmentInfo
from atomforge.env.base.provider import EnvironmentProvider, file_sha256
from atomforge.env.uv.uv import UVEnvironmentProvider
from atomforge_core.env.env import EnvironmentSpec


class FakeEnvironmentProvider(EnvironmentProvider):
    provider_name = "fake"

    def environment_key(self, spec: EnvironmentSpec) -> str:
        return f"fake-{spec.hash()[:8]}"

    def ensure_environment(self, spec: EnvironmentSpec) -> EnvironmentHandle:
        return EnvironmentHandle(
            name=spec.name,
            provider=self.provider_name,
            path=self.install_path / self.provider_name,
        )

    def inspect_environment(self, handle: EnvironmentHandle) -> EnvironmentInfo:
        return EnvironmentInfo(
            handle=handle,
            path=handle.path,
            python_executable=handle.path / ".venv" / "bin" / "python",
        )

    def remove_environment(self, handle: EnvironmentHandle) -> None:
        pass


def test_file_sha256_returns_none_for_missing_file(tmp_path):
    assert file_sha256(tmp_path / "missing.txt") is None


def test_file_sha256_hashes_file_contents(tmp_path):
    path = tmp_path / "file.txt"
    path.write_text("content")

    assert (
        file_sha256(path)
        == "ed7002b439e9ac845f22357d822bac1444730fbdb6016d3ec9"
        "432297b9ec9f73"
    )


def test_base_provider_builds_path_independent_environment_provenance(tmp_path):
    provider = FakeEnvironmentProvider(search_path=(tmp_path,), install_path=tmp_path)
    spec = EnvironmentSpec(
        name="fake-env",
        python="3.12",
        requirements=["fake-base"],
        provider_requirements=["fake-provider"],
    )

    provenance = provider.build_provenance(spec)

    assert provenance.provider == "fake"
    assert provenance.key == provider.environment_key(spec)
    assert provenance.spec_hash == spec.hash()
    assert provenance.python == "3.12"
    assert provenance.requirements == ("fake-base",)
    assert provenance.provider_requirements == ("fake-provider",)
    assert provenance.pyproject_hash is None
    assert provenance.lockfile_hash is None


def test_uv_provider_builds_hashes_for_generated_files(tmp_path):
    provider = UVEnvironmentProvider(search_path=(tmp_path,), install_path=tmp_path)
    env_path = tmp_path / "uv-env"
    env_path.mkdir()
    pyproject_path = env_path / "pyproject.toml"
    lockfile_path = env_path / "uv.lock"
    pyproject_path.write_text("[project]\nname = 'test'\n")
    lockfile_path.write_text("lock")
    spec = EnvironmentSpec(name="uv-env")
    handle = EnvironmentHandle(name="uv-env", provider="uv", path=env_path)

    provenance = provider.build_provenance(spec, handle)

    assert provenance.pyproject_hash == file_sha256(pyproject_path)
    assert provenance.lockfile_hash == file_sha256(lockfile_path)


def test_uv_provider_missing_generated_files_do_not_raise(tmp_path):
    provider = UVEnvironmentProvider(search_path=(tmp_path,), install_path=tmp_path)
    env_path = tmp_path / "uv-env"
    env_path.mkdir()
    spec = EnvironmentSpec(name="uv-env")
    handle = EnvironmentHandle(name="uv-env", provider="uv", path=env_path)

    provenance = provider.build_provenance(spec, handle)

    assert provenance.pyproject_hash is None
    assert provenance.lockfile_hash is None
