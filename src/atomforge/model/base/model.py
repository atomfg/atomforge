from abc import ABC, abstractmethod

from atomforge.env import EnvironmentSpec
from atomforge.model.base import Property, ModelResult
from atomforge.structure import Structure

class Model(ABC):
    """
    Abstract base class for all models. 

    A model is a wrapper to a machine learning interatomic potential. 
    """

    @property
    @abstractmethod
    def model_kind(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def default_environment(self) -> EnvironmentSpec:
        """
        Return an EnvironmentSpec describing the environment required to run this model.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def supported_properties(self) -> frozenset[Property]:
        ...

    def supports(self, *properties: Property) -> bool:
        return all(prop in self.supported_properties for prop in properties)

    @abstractmethod
    def compute(
        self,
        structure: Structure,
        properties: set[Property],
    ) -> ModelResult:
        ...