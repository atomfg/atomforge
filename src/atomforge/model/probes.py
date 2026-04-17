from pydantic import BaseModel, ConfigDict, Field
from typing import Callable, Literal

from atomforge.model.base.spec import ModelSpecT

Accelerator = Literal["cpu", "gpu", "mps"]


class ProbeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    available_accelerators: frozenset[Accelerator] = Field(
        default_factory=lambda: frozenset({"cpu"})
    )
    reasons: dict[Accelerator, str] = Field(default_factory=dict)


ResourceProbe = Callable[[ModelSpecT], ProbeResult]


def torch_probe(model_spec: ModelSpecT) -> ProbeResult:
    try:
        import torch

        available_accelerators: set[Accelerator] = {"cpu"}
        reasons: dict[Accelerator, str] = {}

        if torch.cuda.is_available():
            available_accelerators.add("gpu")
        else:
            reasons["gpu"] = "PyTorch CUDA backend is unavailable."

        mps_backend = getattr(torch.backends, "mps", None)
        if (
            mps_backend is not None
            and mps_backend.is_built()
            and mps_backend.is_available()
        ):
            available_accelerators.add("mps")
        else:
            reasons["mps"] = "PyTorch MPS backend is unavailable."

        return ProbeResult(
            available_accelerators=frozenset(available_accelerators),
            reasons=reasons,
        )
    except ImportError as e:
        return ProbeResult(
            available_accelerators=frozenset({"cpu"}),
            reasons={
                "gpu": f"PyTorch not installed: {e}",
                "mps": f"PyTorch not installed: {e}",
            },
        )
    except Exception as e:
        return ProbeResult(
            available_accelerators=frozenset({"cpu"}),
            reasons={
                "gpu": f"Error during PyTorch probe: {e}",
                "mps": f"Error during PyTorch probe: {e}",
            },
        )
