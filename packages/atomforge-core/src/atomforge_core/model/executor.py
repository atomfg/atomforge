from abc import ABC, abstractmethod
from typing import Generic

from atomforge_core.resources.resource_models import ResolvedResources
from atomforge_core.structure import StructureData

from atomforge_core.property import Property
from atomforge_core.model.result import ModelResult
from atomforge_core.model.spec import ModelSpecT


class ModelExecutor(ABC, Generic[ModelSpecT]):
    def __init__(self, spec: ModelSpecT, resolved_resources: ResolvedResources):
        self.spec = spec
        self.resolved_resources = resolved_resources

    @abstractmethod
    def compute(
        self, structure: StructureData, properties: frozenset[Property]
    ) -> ModelResult:
        raise NotImplementedError
