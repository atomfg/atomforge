from typing import Literal

from atomforge_core.model.spec import ModelSpec

from atomforge_chgnet.definitions import model_kind


class CHGNet(ModelSpec):
    kind: Literal["chgnet"] = model_kind
