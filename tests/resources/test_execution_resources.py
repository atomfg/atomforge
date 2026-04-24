import pytest

from atomforge._core.resources.resource_models import ExecutionResources


def test_execution_resources_init():
    resources = ExecutionResources()
    assert resources is not None


def test_execution_resources_attributes():
    """
    This test is meant to quickly catch if any new attributes are added to the ExecutionResources
    class without updating the test suite. This test failing does not mean that adding a new attribute
    is a bug, but it should be a conscious decision and the test suite should be updated accordingly.
    """
    allowed_attributes = ["accelerator", "precision", "strict"]
    resources = ExecutionResources()

    # Check that only the allowed attributes are present in the ExecutionResources instance
    for attribute in resources.__dict__.keys():
        print(attribute)
        assert attribute in allowed_attributes, (
            f"Unexpected attribute '{attribute}' found in ExecutionResources"
        )

    # Check that all allowed attributes are present
    for attribute in allowed_attributes:
        assert hasattr(resources, attribute), (
            f"Expected attribute '{attribute}' not found in ExecutionResources"
        )
