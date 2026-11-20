from atomforge_core.model.metadata import ModelMetadata, Reference
from atomforge_core.property import Property
from atomforge_core.resources.resource_caps import ResourceCapabilities

# Unique across every installed plugin. Users select the model by this string.
model_kind = "torch-lj"

# The properties the executor can return. The runtime contracts run a single point
# for each of energy and forces when they are declared here.
TorchLJSupportedProperties = frozenset({Property.ENERGY, Property.FORCES})

# The resource knobs the model responds to, with the precisions it supports on
# each accelerator. Set a knob to None if the model ignores it. Torch has no
# float64 on MPS, so MPS runs f32 only. "rocm" (AMD GPUs) is left out until the
# model has run on one; ROCm builds of torch would use the same "cuda" device.
TorchLJResourceCapabilities = ResourceCapabilities(
    accelerator=["cpu", "cuda", "mps"],
    precision={"cpu": ["f32", "f64"], "cuda": ["f32", "f64"], "mps": ["f32"]},
)

TorchLJMetadata = ModelMetadata(
    id=model_kind,
    name="Lennard-Jones (PyTorch)",
    method_family="empirical",
    description="Lennard-Jones pair potential with forces from autograd.",
    references=(
        Reference(
            label="atomforge",
            url="https://github.com/atomfg/atomforge",
            kind="repo",
        ),
    ),
)
