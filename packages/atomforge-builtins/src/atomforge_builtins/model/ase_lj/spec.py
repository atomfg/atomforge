from typing import Annotated, Literal

from atomforge_core.model.spec import ModelSpec, Setting

from atomforge_builtins.model.ase_lj.definitions import model_kind


class LennardJones(ModelSpec):
    environment_profile: Literal["tested", "latest"] = "tested"
    kind: Literal["ase-lj"] = model_kind
    sigma: Annotated[float, Setting] = 1.0
    epsilon: Annotated[float, Setting] = 1.0
    rc: Annotated[float | None, Setting] = None
    ro: Annotated[float | None, Setting] = None
    smooth: Annotated[bool, Setting] = False
