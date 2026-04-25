from __future__ import annotations
from typing import Mapping

from pydantic import BaseModel, Field, ConfigDict, field_validator


def parse_requirement(requirement_str: str) -> tuple[str, str | None]:
    special_characters = ["==", ">=", "<=", "!=", ">", "<", "~=", "@", ";"]
    for char in special_characters:
        if char in requirement_str:
            break
    else:
        # No special characters found, return the requirement as is with no version specifier.
        return requirement_str.strip(), None

    # Split at char
    name, source = requirement_str.split(char, 1)
    return name.strip(), (char + source).strip()


class EnvironmentSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    name: str = Field(
        description="A human-readable name for the environment specification, used for display and debugging purposes."
    )
    python: str | None = Field(
        default=None,
        description="The Python version for the environment specification.",
    )
    requirements: tuple[str, ...] = Field(
        default=(),
        description="A tuple of requirements for the environment specification. Each requirement should be a string in the format accepted by pip, e.g. 'package', 'package==1.2.3', 'package>=1.0,<2.0', 'package @ git+https://...', etc.",
    )
    channels: tuple[str, ...] = Field(
        default=(), description="A tuple of channels for the environment specification."
    )
    extras: Mapping[str, str] = Field(
        default_factory=dict,
        description="A mapping of extra dependencies for the environment specification.",
    )
    provider_requirements: tuple[str, ...] = Field(
        default=(),
        description="Packages required for entry-point discovery. These are not necessarily required for the environment itself, but are needed to load registry providers that may be installed in the environment.",
    )

    @field_validator("requirements", "channels", mode="before")
    @classmethod
    def normalize_string_collections(cls, value):
        return tuple(sorted(set(value)))
    
    @field_validator("python", mode="before")
    def normalize_python_version(cls, value):
        if value is None:
            return None
        value = value.strip()
        if value == "":
            return None
        
        if len(value.split(".")) not in (2, 3):
            raise ValueError(f"Invalid python version specification: '{value}'")
        
        # Only allow numbers and operators (e.g. >=3.10, ==3.9.1, etc. not python=3.10.0-alpha)
        allowed_characters = set("0123456789.><=!,~@")
        if any(char not in allowed_characters for char in value):
            raise ValueError(f"Invalid characters in python version specification: '{value}'")

        return value


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
            "provider_requirements": self.provider_requirements,
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
                if merged[name] is not None and spec is not None and merged[name] != spec:
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
        provider_requirements = self.merge_requirements(
            self.provider_requirements, other.provider_requirements
        )

        return EnvironmentSpec(
            name=f"{self.name}-{other.name}",
            python=python,
            requirements=requirements,
            channels=channels,
            extras=extras,
            provider_requirements=provider_requirements,
        )

    def with_provider_requirements(
        self, requirement: tuple[str, ...]
    ) -> "EnvironmentSpec":
        return self.model_copy(
            update={
                "provider_requirements": tuple(
                    sorted(set(self.provider_requirements) | set(requirement))
                )
            }
        )