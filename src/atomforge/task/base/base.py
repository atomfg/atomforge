from abc import ABC, abstractmethod

from atomforge.model.base import Property
from atomforge.task.base.spec import TaskSpec

class Task(ABC):

    @property
    @abstractmethod
    def task_name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod    
    def required_properties(self) -> frozenset[Property]:
        """
        Return the set of properties that must be computed by the model in order to run this task.
        """
        raise NotImplementedError

    def to_spec(self) -> TaskSpec:
        """
        Convert this task to a TaskSpec, which can be serialized and used to reconstruct the task later.
        """
        raise NotImplementedError
    
