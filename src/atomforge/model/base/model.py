from abc import ABC, abstractmethod

from atomforge.env import EnvironmentSpec
from atomforge.model.base import Property, ModelResult
from atomforge.structure import Structure


class Model(ABC):
    """
    Abstract base class for all models.

    A model is a wrapper to a machine learning interatomic potential.
    """

    supported_properties: frozenset[Property]
    model_kind: str

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls is Model:
            return
        if "supported_properties" not in cls.__dict__:
            raise TypeError(f"{cls.__name__} must define supported_properties")
        if "model_kind" not in cls.__dict__:
            raise TypeError(f"{cls.__name__} must define model_kind")

    @abstractmethod
    def default_environment(self) -> EnvironmentSpec:
        """
        Return an EnvironmentSpec describing the environment required to run this model.
        """
        raise NotImplementedError

    @classmethod
    def supports(cls, *properties: Property) -> bool:
        return all(prop in cls.supported_properties for prop in properties)

    @abstractmethod
    def compute(
        self,
        structure: Structure,
        properties: set[Property],
    ) -> ModelResult: ...
