from typing import Literal

from pydantic import Field

from atomforge_core.model.spec import ModelSpec

from atomforge_template.torch_lj.definitions import model_kind


class TorchLJ(ModelSpec):
    """User-facing settings of the model.

    A spec is a frozen pydantic model that is serialized and sent to the worker.
    Keep it free of heavy imports: it is constructed on the host.
    """

    # The profiles offered by the environment factory. "tested" must be the default.
    environment_profile: Literal["tested", "latest"] = "tested"
    kind: Literal["torch-lj"] = model_kind

    epsilon: float = Field(default=1.0, gt=0, description="Well depth in eV.")
    sigma: float = Field(default=1.0, gt=0, description="Zero crossing in Angstrom.")
