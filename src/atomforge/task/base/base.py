from abc import ABC, abstractmethod

from atomforge.model.base import Property
from atomforge.task.base.spec import TaskSpec


class Task(ABC):
    required_model_properties: frozenset[Property]

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls is Task:
            return
        if "required_model_properties" not in cls.__dict__:
            raise TypeError(f"{cls.__name__} must define required_model_properties")

    @property
    @abstractmethod
    def task_name(self) -> str:
        raise NotImplementedError

    def to_spec(self) -> TaskSpec:
        """
        Convert this task to a TaskSpec, which can be serialized and used to reconstruct the task later.
        """
        raise NotImplementedError
