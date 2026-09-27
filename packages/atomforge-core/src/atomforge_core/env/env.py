from __future__ import annotations
from typing import Mapping

from packaging.requirements import Requirement
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.utils import canonicalize_name

from pydantic import BaseModel, Field, ConfigDict, field_validator


def normalize_distribution_name(name: str) -> str:
    return name.strip().lower().replace("_", "-")


def validate_distribution_name(name: str) -> str:
    stripped = name.strip()
    if not stripped:
        raise ValueError("distribution name must not be empty")
    try:
        requirement = Requirement(stripped)
    except Exception as exc:
        raise ValueError(
            f"distribution names must be bare package names only (got {name!r})"
        ) from exc
    if (
        requirement.url
        or requirement.extras
        or requirement.marker
        or requirement.specifier
    ):
        raise ValueError(
            f"distribution names must be bare package names only (got {name!r})"
        )
    return normalize_distribution_name(requirement.name)


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

    @field_validator("provider_requirements", mode="before")
    @classmethod
    def normalize_provider_requirements(cls, value):
        if value is None:
            return ()
        if isinstance(value, str):
            raise TypeError(
                "provider_requirements must be an iterable of strings, not a single string"
            )

        normalized = []
        for item in value:
            if not isinstance(item, str):
                raise TypeError("provider_requirements must contain only strings")
            normalized.append(validate_distribution_name(item))

        return tuple(sorted(set(normalized)))

    @field_validator("python", mode="before")
    @classmethod
    def normalize_python_version(cls, value):
        if value is None:
            return None
        value = value.strip()
        if value == "":
            return None

        try:
            return str(SpecifierSet(value))
        except InvalidSpecifier as exc:
            raise ValueError(
                f"Invalid Python version specification: {value!r}"
            ) from exc

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
        merged: dict[tuple[str, tuple[str, ...], str], Requirement] = {}
        for raw in (*reqs1, *reqs2):
            requirement = Requirement(raw)
            key = (
                canonicalize_name(requirement.name),
                tuple(sorted(requirement.extras)),
                str(requirement.marker) if requirement.marker else "",
            )
            previous = merged.get(key)
            if previous is None:
                merged[key] = requirement
                continue

            if previous.url or requirement.url:
                if (
                    previous.url != requirement.url
                    or previous.specifier
                    or requirement.specifier
                ):
                    raise ValueError(
                        f"Conflicting direct requirements for package '{key[0]}': "
                        f"'{previous}' vs '{requirement}'"
                    )
                continue

            combined = SpecifierSet(
                ",".join(
                    part
                    for part in (str(previous.specifier), str(requirement.specifier))
                    if part
                )
            )
            previous.specifier = combined

        return tuple(str(merged[key]) for key in sorted(merged))

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
        if python1 and python2:
            return str(SpecifierSet(f"{python1},{python2}"))
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
        return EnvironmentSpec(
            name=self.name,
            python=self.python,
            requirements=self.requirements,
            channels=self.channels,
            extras=self.extras,
            provider_requirements=tuple(
                sorted(set(self.provider_requirements) | set(requirement))
            ),
        )
