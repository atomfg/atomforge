from atomforge_core.model.spec import ModelSpecT
from atomforge_core.resources.resource_probes import Accelerator, ProbeResult


def torch_probe(model_spec: ModelSpecT) -> ProbeResult:
    try:
        import torch

        available_accelerators: set[Accelerator] = {"cpu"}
        reasons: dict[Accelerator, str] = {}

        # ROCm builds of torch expose AMD GPUs through the torch.cuda API;
        # torch.version.hip tells them apart.
        gpu_backend: Accelerator = (
            "rocm" if getattr(torch.version, "hip", None) else "cuda"
        )
        other_backend: Accelerator = "cuda" if gpu_backend == "rocm" else "rocm"
        if torch.cuda.is_available():
            available_accelerators.add(gpu_backend)
        else:
            reasons[gpu_backend] = (
                f"PyTorch {gpu_backend.upper()} backend is unavailable."
            )
        reasons[other_backend] = (
            f"This PyTorch build has no {other_backend.upper()} support."
        )

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
                "cuda": f"PyTorch not installed: {e}",
                "rocm": f"PyTorch not installed: {e}",
                "mps": f"PyTorch not installed: {e}",
            },
        )
    except Exception as e:
        return ProbeResult(
            available_accelerators=frozenset({"cpu"}),
            reasons={
                "cuda": f"Error during PyTorch probe: {e}",
                "rocm": f"Error during PyTorch probe: {e}",
                "mps": f"Error during PyTorch probe: {e}",
            },
        )
