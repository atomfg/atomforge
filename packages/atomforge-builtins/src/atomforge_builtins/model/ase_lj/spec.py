from typing import Literal

from atomforge_core.model.spec import ModelSpec

from atomforge_builtins.model.ase_lj.definitions import model_kind


class LennardJones(ModelSpec):
    kind: Literal["ase-lj"] = model_kind
    sigma: float = 1.0
    epsilon: float = 1.0
    rc: float | None = None
    ro: float | None = None
    smooth: bool = False
