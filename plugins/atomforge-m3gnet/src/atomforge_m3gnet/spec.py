from typing import Literal

from atomforge_core.model.spec import ModelSpec

from atomforge_m3gnet.definitions import model_kind


class M3GNet(ModelSpec):
    kind: Literal["m3gnet"] = model_kind
