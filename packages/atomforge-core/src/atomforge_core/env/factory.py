from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, Generic, TypeVar, ClassVar
from typing_extensions import Self

from atomforge_core.env.env import EnvironmentSpec
from dataclasses import dataclass
from packaging.specifiers import SpecifierSet

SpecT = TypeVar("SpecT")


@dataclass(frozen=True)
class DependencySummary:
    base_requirements: tuple[str, ...] = ()
    possible_requirements: tuple[str, ...] = ()
    python: str | None = None
    possible_python: tuple[str, ...] = ()
    channels: tuple[str, ...] = ()
    notes: str | None = None

    def __post_init__(self) -> None:
        if self.python is not None:
            object.__setattr__(self, "python", str(SpecifierSet(self.python)))
        object.__setattr__(
            self,
            "possible_python",
            tuple(str(SpecifierSet(value)) for value in self.possible_python),
        )

    def declared_requirements(self) -> frozenset[str]:
        return frozenset(self.base_requirements) | frozenset(self.possible_requirements)


class EnvironmentFactory(ABC, Generic[SpecT]):
    """
    Abstract base class for environment factories.

    Implementations must be default-constructible and callable with a single
    argument of type `SpecT`, returning an `EnvironmentSpec`.

    Registry-level provider requirements are injected automatically during
    registration and must not be supplied by plugin authors.

    `build(spec)` must be pure and deterministic with respect to `spec`.
    Implementations must not depend on instance state; any configuration needed
    to resolve the environment should be encoded in the spec.
    """

    dependency_summary: ClassVar[DependencySummary] = DependencySummary()

    def __init__(
        self,
        provider_requirements: tuple[str, ...] = (),
    ) -> None:
        self._provider_requirements = provider_requirements

    def __call__(self, spec: SpecT) -> EnvironmentSpec:
        env = self.build(spec)

        if self._provider_requirements:
            env = env.with_provider_requirements(self._provider_requirements)

        self.validate(env)
        return env

    @abstractmethod
    def build(self, spec: SpecT) -> EnvironmentSpec:
        raise NotImplementedError

    def validate(self, env: EnvironmentSpec) -> None:
        declared = self.dependency_summary.declared_requirements()
        actual = frozenset(env.requirements)
        undeclared = actual - declared
        if undeclared:
            raise ValueError(
                f"{self.__class__.__name__} returned undeclared requirements: {sorted(undeclared)}"
            )

        # Validate Python
        if self.dependency_summary.python is not None:
            if env.python is None:
                raise ValueError(
                    f"{self.__class__.__name__} did not specify a Python version, but dependency summary declares Python {self.dependency_summary.python}"
                )
            elif env.python != self.dependency_summary.python:
                raise ValueError(
                    f"{self.__class__.__name__} returned Python {env.python}, but dependency summary declares Python {self.dependency_summary.python}"
                )
        elif self.dependency_summary.possible_python:
            if env.python not in self.dependency_summary.possible_python:
                raise ValueError(
                    f"{self.__class__.__name__} returned Python {env.python}, but dependency summary declares one of {self.dependency_summary.possible_python}"
                )

        # Validate channels
        if self.dependency_summary.channels:
            missing_channels = set(self.dependency_summary.channels) - set(env.channels)
            if missing_channels:
                raise ValueError(
                    f"{self.__class__.__name__} is missing required channels: {sorted(missing_channels)}"
                )

    def with_provider_requirements(
        self,
        requirements: list[str] | tuple[str, ...],
    ) -> Self:
        merged = tuple(sorted(set(self._provider_requirements) | set(requirements)))
        return type(self)(provider_requirements=merged)


def environment_factory_from_callable(
    func: Callable[[SpecT], EnvironmentSpec],
    dependency_summary: DependencySummary | None = None,
) -> type[EnvironmentFactory[SpecT]]:
    if not callable(func):
        raise ValueError("Provided environment factory must be callable")

    class CallableEnvironmentFactory(EnvironmentFactory[SpecT]):
        def build(self, spec: SpecT) -> EnvironmentSpec:
            return func(spec)

    factory_cls = CallableEnvironmentFactory
    if dependency_summary is not None:
        factory_cls.dependency_summary = dependency_summary
    return factory_cls
