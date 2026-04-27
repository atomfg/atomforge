from atomforge_core.model.metadata import ModelMetadata, Reference
from atomforge_core.property import Property
from atomforge_core.resources.resource_caps import ResourceCapabilities

model_kind = "mace"

MACESupportedProperties = frozenset({Property.ENERGY, Property.FORCES})

MACEResourceCapabilities = ResourceCapabilities(
    accelerator=["cpu", "gpu"],
    precision=["f32", "f64"],
)

MACEMetadata = ModelMetadata(
    id=model_kind,
    name="MACE",
    method_family="mlip",
    references=(
        Reference(
            label="GitHub Repository",
            url="https://github.com/ACEsuit/mace",
            kind="repo",
        ),
        Reference(
            label="Paper",
            url="https://openreview.net/forum?id=YPpSngE-ZU",
            kind="paper",
        ),
    ),
)
