from abc import abstractmethod, ABC

from .spec import ModelSpecT
from .property import Property
from .result import ModelResult
from atomforge.structure import Structure

from typing import Generic


class ModelExecutor(ABC, Generic[ModelSpecT]):
    def __init__(self, spec: ModelSpecT):
        self.spec = spec

    @abstractmethod
    def compute(
        self, structure: Structure, properties: frozenset[Property]
    ) -> ModelResult:
        raise NotImplementedError
