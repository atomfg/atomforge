import pytest

from atomforge.task.base.resources import ExecutionResources

def test_execution_resources_init():
    resources = ExecutionResources()
    assert resources is not None
