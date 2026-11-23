from typing import Annotated, Literal

from pydantic import Field

from atomforge_core.model.spec import ModelSpec, Setting
from atomforge_core.model.weights import LocalWeights

from atomforge_template.definitions import model_kind


class TorchLJ(ModelSpec):
    """User-facing settings of the model.

    A spec is a frozen pydantic model that is serialized and sent to the worker.
    Keep it free of heavy imports: it is constructed on the host.

    Every field has a role, given with Annotated:

    - Variant: chooses the trained parameters (a checkpoint). Its type must be
      enumerable (Literal, bool, or their unions with None), so that
      TorchLJ.variants() can list every trained model. Lennard-Jones has no
      trained parameters, so this spec has no variant field and one variant,
      "default". A model with checkpoints would declare, for example:

          model: Annotated[Literal["small", "large"], Variant] = "small"

      Where a variant field has no effect for some values of another, bring it
      to None in a mode="before" validator, so each trained model is one
      variant.
    - Setting: everything else the executor uses, even when it changes the
      numbers (precision modes, dispersion corrections, parameters as here).
    - kind and environment_profile are reserved and take no marker.
    """

    # The profiles offered by the environment factory. "tested" must be the default.
    environment_profile: Literal["tested", "latest"] = "tested"
    kind: Literal["torch-lj"] = model_kind

    epsilon: Annotated[float, Setting] = Field(
        default=1.0, gt=0, description="Well depth in eV."
    )
    sigma: Annotated[float, Setting] = Field(
        default=1.0, gt=0, description="Zero crossing in Angstrom."
    )
    # Parameters from a local file, for example a model fine-tuned with the
    # provider's own package. Recognised by its type, so it takes no marker;
    # declaring it is how the plugin says it can load local parameters. When
    # set, the file's parameters replace epsilon and sigma. Leave it out if the
    # model cannot load local parameters.
    weights: LocalWeights | None = Field(
        default=None,
        description=(
            "Parameters from a local JSON file with keys 'epsilon' and 'sigma', "
            "replacing the spec's own."
        ),
    )
