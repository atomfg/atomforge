from atomforge_core.model.metadata import ModelMetadata, Reference
from atomforge_core.property import Property
from atomforge_core.resources.resource_caps import ResourceCapabilities

model_kind = "m3gnet"

M3GNetSupportedProperties = frozenset({Property.ENERGY, Property.FORCES})

M3GNetResourceCapabilities = ResourceCapabilities(
    accelerator=["cpu"],
)

M3GNetMetadata = ModelMetadata(
    id=model_kind,
    name="M3GNet",
    method_family="mlip",
    references=(
        Reference(
            label="GitHub Repository",
            url="https://github.com/materialyzeai/m3gnet",
            kind="repo",
        ),
        Reference(label="Paper", url="https://arxiv.org/abs/2202.02450", kind="paper"),
    ),
)

REQUIREMENTS = [
    "m3gnet==0.2.4",
    "ase==3.22.1",
    "tensorflow>=2.13,<2.16",
    "keras<3",
]
