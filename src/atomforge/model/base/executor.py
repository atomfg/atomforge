from abc import abstractmethod, ABC

from .spec import ModelSpecT
from .property import Property
from .result import ModelResult
from atomforge.structure import Structure
from atomforge.task.base.resources import ResolvedResources

from typing import Generic


class ModelExecutor(ABC, Generic[ModelSpecT]):
    def __init__(self, spec: ModelSpecT, resolved_resources: ResolvedResources):
        self.spec = spec
        self.resolved_resources = resolved_resources

    @abstractmethod
    def compute(
        self, structure: Structure, properties: frozenset[Property]
    ) -> ModelResult:
        raise NotImplementedError
