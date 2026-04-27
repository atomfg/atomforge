from typing import Literal

from atomforge_core.model.spec import ModelSpec

from atomforge_mace.definitions import model_kind


class MACE(ModelSpec):
    kind: Literal["mace"] = model_kind
    model: str = "medium"
    dispersion: bool = False
