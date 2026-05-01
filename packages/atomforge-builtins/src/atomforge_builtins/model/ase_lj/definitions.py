from atomforge_core.model.metadata import ModelMetadata, Reference
from atomforge_core.property import Property
from atomforge_core.resources.resource_caps import ResourceCapabilities

description = """Lennard-Jones potential implemented in the Atomic Simulation Environment (ASE).
"""

model_kind = "ase-lj"
LennardJonesSupportedProperties = frozenset({Property.ENERGY, Property.FORCES})

LennardJonesMetadata = ModelMetadata(
    id=model_kind,
    name="ASE Lennard-Jones",
    method_family="empirical",
    references=(
        Reference(label="ASE Documentation", url="https://ase-lib.org/", kind="docs"),
    ),
    description=description,
)

LennardJonesResourceCapabilities = ResourceCapabilities(
    accelerator=["cpu"], precision=None
)
