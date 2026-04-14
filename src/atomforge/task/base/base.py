from abc import ABC, abstractmethod

from atomforge.env import EnvironmentSpec
from atomforge.model.base import Property
from atomforge.task.base.spec import TaskSpec

from dataclasses import dataclass


@dataclass(slots=True)
class TaskCapabilitySpec:
    required: frozenset[Property]
    optional: frozenset[Property] = frozenset()

    def __post_init__(self):
        if self.required.intersection(self.optional):
            raise ValueError("A property cannot be both required and optional.")


class Task(ABC):
    capability_spec: TaskCapabilitySpec
    task_name: str

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls is Task:
            return
        if "task_name" not in cls.__dict__:
            raise TypeError(f"{cls.__name__} must define task_name")
        if "capability_spec" not in cls.__dict__:
            raise TypeError(f"{cls.__name__} must define capability_spec")

    @abstractmethod
    def to_spec(self) -> TaskSpec:
        """
        Convert this task to a TaskSpec, which can be serialized and used to reconstruct the task later.
        """
        raise NotImplementedError

    @abstractmethod
    def _required_model_properties(self) -> frozenset[Property]:
        """
        Return the set of properties that a model must be able to compute in order
        to execute this task _instance_.

        If task configuration changes what properties are necessary, this method
        should reflect that.

        """
        raise NotImplementedError

    @property
    def required_model_properties(self) -> frozenset[Property]:
        return self._required_model_properties()

    @abstractmethod
    def executor_environment(self) -> EnvironmentSpec:
        """
        Return an EnvironmentSpec describing the environment necessary to execute this task.
        """
        raise NotImplementedError
