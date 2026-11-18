from atomforge_core.model.metadata import ModelMetadata, Reference
from atomforge_core.property import Property
from atomforge_core.resources.resource_caps import ResourceCapabilities

# Unique across every installed plugin. Users select the model by this string.
model_kind = "torch-lj"

# The properties the executor can return. The runtime contracts run a single point
# for each of energy and forces when they are declared here.
TorchLJSupportedProperties = frozenset({Property.ENERGY, Property.FORCES})

# The resource knobs the model responds to. Set a knob to None if the model ignores
# it. MPS is left out because torch has no float64 on MPS, and the resolver's
# defaults (MPS first on macOS, f64 first) would pick that unsupported combination.
TorchLJResourceCapabilities = ResourceCapabilities(
    accelerator=["cpu", "gpu"], precision=["f32", "f64"]
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
