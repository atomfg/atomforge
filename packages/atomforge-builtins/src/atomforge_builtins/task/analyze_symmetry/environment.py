from atomforge_core.env.env import EnvironmentSpec
from atomforge_core.env.factory import (
    DependencySummary,
    environment_factory_from_callable,
)

AnalyzeSymmetryEnvironmentFactory = environment_factory_from_callable(
    lambda spec: EnvironmentSpec(name="analyze_symmetry", requirements=["ase", "pymatgen"]),
    DependencySummary(base_requirements=["ase", "pymatgen"]),
)
