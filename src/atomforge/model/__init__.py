from .base import Model, ModelResult, Property
from .ase_lennard_jones import ASELennardJones

models = {
    "ase_lennard_jones": ASELennardJones,}

__all__ = ["Model", "ModelResult", "Property"]
