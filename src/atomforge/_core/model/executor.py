from abc import ABC, abstractmethod
from typing import Generic

from atomforge._core.resources.resource_models import ResolvedResources
from atomforge._core.structure import StructureData

from atomforge._core.property import Property
from atomforge._core.model.result import ModelResult
from atomforge._core.model.spec import ModelSpecT


class ModelExecutor(ABC, Generic[ModelSpecT]):
    def __init__(self, spec: ModelSpecT, resolved_resources: ResolvedResources):
        self.spec = spec
        self.resolved_resources = resolved_resources

    @abstractmethod
    def compute(
        self, structure: StructureData, properties: frozenset[Property]
    ) -> ModelResult:
        raise NotImplementedError
