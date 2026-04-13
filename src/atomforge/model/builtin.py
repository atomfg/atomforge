from .registry import ModelRegistry

from .ase_lennard_jones import ASELennardJones
from .chgnet_model import CHGNet

def get_default_model_registry():
    registry = ModelRegistry()
    registry.register("ase_lennard_jones", ASELennardJones)
    registry.register("chgnet", CHGNet)
    return registry

