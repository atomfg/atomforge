from abc import ABC, abstractmethod

from atomforge.model.base import Property, Model
from atomforge import Structure

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
    
    @abstractmethod
    def run(self, structure: Structure, model: Model):
        raise NotImplementedError