from atomforge_core.resources.resource_models import ExecutionResources


def test_execution_resources_init():
    resources = ExecutionResources()
    assert resources is not None


def test_execution_resources_attributes():
    allowed_attributes = ["accelerator", "precision", "strict"]
    resources = ExecutionResources()

    for attribute in resources.__dict__.keys():
        assert attribute in allowed_attributes, (
            f"Unexpected attribute '{attribute}' found in ExecutionResources"
        )

    for attribute in allowed_attributes:
        assert hasattr(resources, attribute), (
            f"Expected attribute '{attribute}' not found in ExecutionResources"
        )

