from atomforge_core.env.env import EnvironmentSpec
from atomforge_core.env.factory import DependencySummary, EnvironmentFactory

from atomforge_template.spec import TorchLJ

# The worker environment. These are the model's real dependencies; the host never
# installs them. "tested" pins what the plugin is tested against, "latest" lets
# users opt into newer versions. numpy is listed because ModelResult holds numpy
# arrays and torch does not require numpy. Its pin must also exist on the
# CPU-only torch index that CI uses, which mirrors numpy with some delay.
TESTED_REQUIREMENTS = ("torch==2.15.0", "numpy==2.5.4")
LATEST_REQUIREMENTS = ("torch>=2.15.0", "numpy>=2.5.4")

ENVIRONMENT_PROFILES = {
    "tested": EnvironmentSpec(
        name="torch-lj", python="==3.12.*", requirements=TESTED_REQUIREMENTS
    ),
    "latest": EnvironmentSpec(
        name="torch-lj", python=">=3.12", requirements=LATEST_REQUIREMENTS
    ),
}


class TorchLJEnvironmentFactory(EnvironmentFactory[TorchLJ]):
    # Every requirement and Python version that build() can return must be declared
    # here. The contracts check this.
    dependency_summary = DependencySummary(
        possible_requirements=TESTED_REQUIREMENTS + LATEST_REQUIREMENTS,
        possible_python=("==3.12.*", ">=3.12"),
    )

    def build(self, spec: TorchLJ) -> EnvironmentSpec:
        # Must be deterministic in the spec. Do not inspect the machine here.
        return ENVIRONMENT_PROFILES[spec.environment_profile]
