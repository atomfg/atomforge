import pytest
from atomforge import ExecutionResources

def test_execution_resources_init():
    resources = ExecutionResources()
    assert resources is not None

