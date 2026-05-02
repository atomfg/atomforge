from atomforge_core.model.metadata import ModelMetadata, Reference
from atomforge_core.property import Property
from atomforge_core.resources.resource_caps import ResourceCapabilities

model_kind = "chgnet"

CHGNetSupportedProperties = frozenset({Property.ENERGY, Property.FORCES, Property.ENERGIES, Property.MAGMOMS, Property.STRESS})

CHGNetResourceCapabilities = ResourceCapabilities(
    accelerator=["cpu", "gpu", "mps"],
)

CHGNetMetadata = ModelMetadata(
    id=model_kind,
    name="CHGNet",
    method_family="mlip",
    references=(
        Reference(
            label="GitHub Repository",
            url="https://github.com/CederGroupHub/chgnet",
            kind="repo",
        ),
        Reference(
            label="Paper",
            url="https://www.nature.com/articles/s42256-023-00716-3",
            kind="paper",
        ),
    ),
)
