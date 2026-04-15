from .registry import ModelRegistry

from .ase_lj import ASELennardJones
from .chgnet_model import CHGNet
from .mace_model import MACE


def get_default_model_registry():
    registry = ModelRegistry()
    registry.register("ase_lennard_jones", ASELennardJones)
    registry.register("chgnet", CHGNet)
    registry.register("mace", MACE)

    return registry
