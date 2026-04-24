import pytest

from atomforge._builtins.model.ase_lj import LennardJones, LennardJonesExecutor
from atomforge._core.resources.resource_models import ResolvedResources

@pytest.fixture
def model_executor():
    resources = ResolvedResources(accelerator="cpu", precision=None)
    model = LennardJones(sigma=0.5, epsilon=2)
    executor = LennardJonesExecutor(model, resources)
    return executor
