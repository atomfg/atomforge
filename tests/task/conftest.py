import pytest

from atomforge.model.ase_lj import LennardJones, LennardJonesExecutor
from atomforge.task.core.resources import ResolvedResources

@pytest.fixture
def model_executor():
    resources = ResolvedResources(accelerator="cpu", precision=None)
    model = LennardJones(sigma=0.5, epsilon=2)
    executor = LennardJonesExecutor(model, resources)
    return executor
