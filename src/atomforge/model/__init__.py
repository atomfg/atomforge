from .base import Model, ModelResult, Property
from .ase_lennard_jones import ASELennardJones
from .chgnet_model import CHGNet

models = {
    "ase_lennard_jones": ASELennardJones,
    "CHGNet": CHGNet,}

__all__ = ["Model", "ModelResult", "Property"]
