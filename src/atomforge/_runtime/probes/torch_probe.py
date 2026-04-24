from atomforge._core.model.spec import ModelSpecT
from atomforge._core.resources.resource_probes import Accelerator, ProbeResult

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