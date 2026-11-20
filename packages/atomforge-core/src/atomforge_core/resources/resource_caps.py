from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Accelerator = Literal["cpu", "cuda", "rocm", "mps"]
Precision = Literal["f32", "f64"]


class ResourceCapabilities(BaseModel):
    """
    ResourceCapabilities represents which knobs of ExecutionResources a model supports.
    This is used for validating requested resources and for resolving defaults.

    If a field is None, it means that the model does not meaningfully use the corresponding resource.
    For example, if precision is None it means that the model cannot take advantage of higher/lower
    precision and will perform the same regardless of the precision specified in ExecutionResources.

    A model that uses both knobs declares its precisions per accelerator, since an
    accelerator may not support every precision (torch has no float64 on MPS):

        ResourceCapabilities(
            accelerator=["cpu", "cuda", "mps"],
            precision={"cpu": ["f32", "f64"], "cuda": ["f32", "f64"], "mps": ["f32"]},
        )

    A plain list of precisions is for models that do not use the accelerator knob.
    """

    model_config = ConfigDict(extra="forbid")
    accelerator: list[Accelerator] | None = Field(
        default=None,
        description="The accelerator backends the model supports.",
    )
    precision: dict[Accelerator, list[Precision]] | list[Precision] | None = Field(
        default=None,
        description=(
            "The numerical precisions the model supports: per accelerator when the "
            "model uses the accelerator knob, otherwise a list."
        ),
    )

    @model_validator(mode="after")
    def _check_declaration(self) -> "ResourceCapabilities":
        if self.accelerator is not None and len(self.accelerator) == 0:
            raise ValueError(
                "accelerator must list at least one accelerator, or be None"
            )
        if self.precision is None:
            return self
        if self.accelerator is None:
            if isinstance(self.precision, dict):
                raise ValueError(
                    "precision per accelerator needs the accelerators declared; "
                    "without them, give a list"
                )
            if len(self.precision) == 0:
                raise ValueError(
                    "precision must list at least one precision, or be None"
                )
            return self
        if not isinstance(self.precision, dict):
            raise ValueError(
                "with accelerators declared, give the precisions per accelerator, "
                'e.g. {"cpu": ["f32", "f64"], "mps": ["f32"]}'
            )
        if set(self.precision) != set(self.accelerator):
            raise ValueError(
                f"precision keys {sorted(self.precision)} must equal the declared "
                f"accelerators {sorted(self.accelerator)}"
            )
        empty = [name for name, precisions in self.precision.items() if not precisions]
        if empty:
            raise ValueError(f"no precision declared for {sorted(empty)}")
        return self

    def precisions_on(self, accelerator: Accelerator | None) -> list[Precision] | None:
        """The precisions supported on an accelerator (None: the knob is unused).

        For a model that does not use the accelerator knob, pass None.
        """
        if self.precision is None:
            return None
        if isinstance(self.precision, list):
            return list(self.precision)
        if accelerator is None:
            raise ValueError("this model declares its precisions per accelerator")
        return list(self.precision.get(accelerator, []))

    def pairs(self) -> list[tuple[Accelerator | None, Precision | None]]:
        """Every declared (accelerator, precision) pair, None for an unused knob."""
        accelerators: list[Accelerator | None] = (
            list(self.accelerator) if self.accelerator is not None else [None]
        )
        result: list[tuple[Accelerator | None, Precision | None]] = []
        for accelerator in accelerators:
            precisions = self.precisions_on(accelerator)
            for precision in precisions if precisions is not None else [None]:
                result.append((accelerator, precision))
        return result
