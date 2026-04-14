from __future__ import annotations

from pathlib import Path
from typing import Mapping

from pydantic import BaseModel, Field, ConfigDict, field_validator


def parse_requirement(requirement_str: str) -> tuple[str, str | None]:
    if "@" in requirement_str:
        # Handle VCS or local path requirements,
        # which can have the form "package @ git+https://..."
        # or "package @ file:///path/to/package"
        name, source = requirement_str.split("@", 1)
        return name.strip(), source.strip()
    elif "==" in requirement_str:
        name, version_spec = requirement_str.split("==", 1)
        return name.strip(), "==" + version_spec.strip()
    elif ">=" in requirement_str:
        name, version_spec = requirement_str.split(">=", 1)
        return name.strip(), ">=" + version_spec.strip()
    elif "<=" in requirement_str:
        name, version_spec = requirement_str.split("<=", 1)
        return name.strip(), "<=" + version_spec.strip()
    elif ">" in requirement_str:
        name, version_spec = requirement_str.split(">", 1)
        return name.strip(), ">" + version_spec.strip()
    elif "<" in requirement_str:
        name, version_spec = requirement_str.split("<", 1)
        return name.strip(), "<" + version_spec.strip()
    else:
        return requirement_str.strip(), None


class EnvironmentSpec(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    python: str | None = None
    requirements: tuple[str, ...] = ()
    channels: tuple[str, ...] = ()
    extras: Mapping[str, str] = Field(default_factory=dict)

    @field_validator("requirements", "channels", mode="before")
    @classmethod
    def normalize_string_collections(cls, value):
        if value is None:
            return ()
        return tuple(sorted(set(value)))

    def hash(self) -> str:
        import hashlib
        import json

        # Create a hash of the environment specification for caching purposes
        # Excluding the name from the hash, since it's just for human readability and doesn't affect the environment itself.
        env_dict = {
            "python": self.python,
            "requirements": self.requirements,
            "channels": self.channels,
            "extras": self.extras,
        }
        env_json = json.dumps(env_dict, sort_keys=True)
        return hashlib.sha256(env_json.encode()).hexdigest()

    def name_with_hash(self) -> str:
        return f"{self.name}-{self.short_hash()}"

    def short_hash(self) -> str:
        return self.hash()[:16]

    def extras_merge(
        self, extras: Mapping[str, str], others: Mapping[str, str]
    ) -> Mapping[str, str]:
        merged = {}
        for key in sorted(set(extras.keys()) | set(others.keys())):
            # If key in both they need to match otherwise we have a conflict and can't merge.
            if key in extras and key in others:
                if extras[key] != others[key]:
                    raise ValueError(
                        f"Conflict in extras for key '{key}': '{extras[key]}' vs '{others[key]}'"
                    )
                merged[key] = extras[key]
            elif key in extras:  # If only in one, just take it
                merged[key] = extras[key]
            else:  # Same as above, but for the other dict.
                merged[key] = others[key]
        return merged

    def merge_requirements(
        self, reqs1: tuple[str, ...], reqs2: tuple[str, ...]
    ) -> tuple[str, ...]:
        """
        Merge two sets of requirements, ensuring that there are no conflicts.
        """
        regs1 = list(parse_requirement(req) for req in reqs1)
        regs2 = list(parse_requirement(req) for req in reqs2)

        merged = {}
        for name, spec in regs1 + regs2:
            if name in merged:
                if merged[name] != spec:
                    raise ValueError(
                        f"Conflict in requirements for package '{name}': '{merged[name]}' vs '{spec}'"
                    )
            merged[name] = spec

        # Sort the merged requirements by package name for consistency, and reconstruct the requirement strings.
        merged = dict(sorted(merged.items()))

        return tuple(
            f"{name}{spec}" if spec is not None else name
            for name, spec in merged.items()
        )

    def merge_channels(
        self, channels1: tuple[str, ...], channels2: tuple[str, ...]
    ) -> tuple[str, ...]:
        """
        Merge two sets of channels, ensuring that there are no duplicates.
        """
        return tuple(sorted(set(channels1) | set(channels2)))

    def merge_python(self, python1: str | None, python2: str | None) -> str | None:
        """
        Merge two python version specifications, ensuring that there are no conflicts.
        """
        if python1 and python2 and python1 != python2:
            raise ValueError(f"Conflict in python versions: '{python1}' vs '{python2}'")
        return python1 or python2

    def __add__(self, other: EnvironmentSpec) -> EnvironmentSpec:
        requirements = self.merge_requirements(self.requirements, other.requirements)
        channels = self.merge_channels(self.channels, other.channels)
        extras = self.extras_merge(self.extras, other.extras)
        python = self.merge_python(self.python, other.python)

        return EnvironmentSpec(
            name=f"{self.name}-{other.name}",
            python=python,
            requirements=requirements,
            channels=channels,
            extras=extras,
        )


class EnvironmentHandle(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    provider: str
    path: Path


class EnvironmentInfo(BaseModel):
    model_config = ConfigDict(frozen=True)
    handle: EnvironmentHandle
    path: Path | None
    python_executable: Path | None
    metadata: Mapping[str, str] = Field(default_factory=dict)

    @property
    def exists(self) -> bool:
        return (
            self.path is not None
            and self.path.exists()
            and self.python_executable is not None
            and self.python_executable.exists()
        )
